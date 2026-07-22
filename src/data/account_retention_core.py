"""
Account-level Retention Forecasting (with right-censoring)
==========================================================

Consumes an account-level table where each ROW is one account, with columns:

    ACCOUNT_OPEN_DATE    - when the account was acquired (day 0)
    ACCOUNT_CLOSED_DATE  - when it closed; BLANK/NULL if still open
    + optional segment columns (channel, audience, branch_online, device, ...)

Produces per-segment Kaplan-Meier survival curves that correctly handle
still-open accounts as right-censored observations.

Adapted from the standalone account_retention.py for Apex integration.
Updated to use FITB monthly acquisition schedule (~124.6K accounts).
"""

from __future__ import annotations

import calendar
import datetime as _dt
import numpy as np
import pandas as pd

from src.data.seeds._dates import YESTERDAY
from src.data.retention_model_core import (
    _curve_specs, neg_log_likelihood, fit_curve, SegmentFit,
    retention_on_date, portfolio_retention_on_date, shrink_survival,
    survival_sbg,
)


# -----------------------------------------------------------------------------
# 1. Kaplan-Meier from account-level tenures
# -----------------------------------------------------------------------------

def kaplan_meier(tenure_days: np.ndarray, closed: np.ndarray):
    """Kaplan-Meier survival estimate."""
    tenure_days = np.asarray(tenure_days, float)
    closed = np.asarray(closed, bool)
    n = len(tenure_days)
    t_max = int(np.max(tenure_days)) if n else 0

    grid = np.arange(0, t_max + 1)
    s = np.ones(t_max + 1)
    surv = 1.0
    for t in range(1, t_max + 1):
        at_risk = np.sum(tenure_days >= t)
        d_t = np.sum((tenure_days == t) & closed)
        if at_risk > 0 and d_t > 0:
            surv *= (1.0 - d_t / at_risk)
        s[t] = surv
    return grid, s


def _effective_counts(t_grid, s_km, n0):
    """Convert a KM survival curve into pseudo cohort counts."""
    n_t = np.maximum(np.round(n0 * s_km), 0).astype(float)
    n_t[0] = n0
    for i in range(1, len(n_t)):
        n_t[i] = min(n_t[i], n_t[i - 1])
    return t_grid.astype(float), n_t


# -----------------------------------------------------------------------------
# 2. Build tenures from an account dataframe
# -----------------------------------------------------------------------------

def compute_tenures(df: pd.DataFrame,
                    open_col: str = "ACCOUNT_OPEN_DATE",
                    closed_col: str = "ACCOUNT_CLOSED_DATE",
                    snapshot: _dt.date | None = None) -> pd.DataFrame:
    snapshot = snapshot or _dt.date.today()
    snap = pd.Timestamp(snapshot)
    out = df.copy()
    out[open_col] = pd.to_datetime(out[open_col])
    out[closed_col] = pd.to_datetime(out[closed_col], errors="coerce")

    out["is_closed"] = out[closed_col].notna()
    end = out[closed_col].where(out["is_closed"], snap)
    out["tenure_days"] = (end - out[open_col]).dt.days

    bad = out["tenure_days"].isna() | (out["tenure_days"] < 0) | out[open_col].isna()
    if bad.any():
        out = out.loc[~bad].copy()
    return out


# -----------------------------------------------------------------------------
# 3. Fit a segment directly from account rows
# -----------------------------------------------------------------------------

def fit_segment_from_accounts(df_seg: pd.DataFrame, segment: str = "ALL",
                              holdout_frac: float = 0.30,
                              verbose: bool = False) -> SegmentFit:
    """KM -> pseudo counts -> fit & select best curve."""
    t_grid, s_km = kaplan_meier(df_seg["tenure_days"].values,
                                df_seg["is_closed"].values)
    n0 = float(len(df_seg))
    t_obs, n_obs = _effective_counts(t_grid, s_km, n0)
    obs_ret = n_obs / n0

    if len(t_obs) < 4:
        raise ValueError(f"Segment '{segment}' has too little tenure spread to fit.")

    split_t = t_obs[int(len(t_obs) * (1 - holdout_frac))]
    train = t_obs <= split_t
    specs = _curve_specs()
    mae, fits = {}, {}
    for name, spec in specs.items():
        p, _ = fit_curve(spec, t_obs[train], n_obs[train], n0)
        pred = spec.survival(t_obs[~train], *p)
        mae[name] = float(np.mean(np.abs(pred - obs_ret[~train]))) if (~train).any() else np.nan
        fits[name] = (spec, p)
    best = min(mae, key=mae.get)
    spec = specs[best]
    p_full, _ = fit_curve(spec, t_obs, n_obs, n0)
    return SegmentFit(segment=segment, best_model=best,
                      params=dict(zip(spec.param_names, p_full)),
                      survival_fn=spec.survival, raw_params=p_full,
                      holdout_mae=mae, n0=n0)


def fit_all_segments(df: pd.DataFrame, segment_cols: list[str] | None = None,
                     open_col="ACCOUNT_OPEN_DATE", closed_col="ACCOUNT_CLOSED_DATE",
                     snapshot: _dt.date | None = None, verbose: bool = False):
    """Returns (seg_fits dict, pooled_fit)."""
    df = compute_tenures(df, open_col, closed_col, snapshot)
    pooled_fit = fit_segment_from_accounts(df, "POOLED", verbose=verbose)
    seg_fits = {}
    if segment_cols:
        for key, grp in df.groupby(segment_cols):
            name = key if isinstance(key, str) else " | ".join(map(str, key))
            try:
                seg_fits[name] = fit_segment_from_accounts(grp, name, verbose=verbose)
            except ValueError:
                pass
    return seg_fits, pooled_fit


# -----------------------------------------------------------------------------
# 4. FITB monthly acquisition schedule
# -----------------------------------------------------------------------------

def _fitb_monthly_open_schedule(rng):
    """Monthly new-household acquisition schedule matching FITB actuals (wiki):
      * 2025 full year: 83,300 HHs (~6,940/mo, mild ramp through the year).
      * 2026 YTD through May: 41,315 HHs, pacing up toward the 115K annual
        run-rate (May pacing ~9,080/mo). Partial June up to the June 1 snapshot.
    Returns a list of (year, month, count). Total ~124.6K.
    """
    sched = []
    # 2025: 83,300 spread with a gentle ramp (Jan lighter, Dec heavier)
    base_2025 = 83_300
    weights_25 = np.linspace(0.85, 1.15, 12)          # mild upward ramp
    counts_25 = np.round(base_2025 * weights_25 / weights_25.sum()).astype(int)
    counts_25[-1] += base_2025 - counts_25.sum()       # fix rounding
    for m, c in enumerate(counts_25, start=1):
        sched.append((2025, m, int(c)))
    # 2026 Jan–May: 41,315 ramping toward ~9,080/mo (May pacing)
    ytd_2026 = 41_315
    weights_26 = np.array([0.85, 0.90, 0.98, 1.05, 1.12])  # Jan..May ramp
    counts_26 = np.round(ytd_2026 * weights_26 / weights_26.sum()).astype(int)
    counts_26[-1] += ytd_2026 - counts_26.sum()
    for m, c in enumerate(counts_26, start=1):
        sched.append((2026, m, int(c)))
    # 2026 June 1 snapshot: no full month of June acquisition observed yet
    return sched


# -----------------------------------------------------------------------------
# 5. Synthetic FITB account generator
# -----------------------------------------------------------------------------

def make_synthetic_accounts(seed=7, total=None) -> tuple[pd.DataFrame, _dt.date]:
    """Synthetic FITB checking-account table calibrated to Project Velocity
    retention benchmarks. Uses realistic monthly acquisition schedule
    (~124.6K accounts from Jan 2025 – May 2026).

    Returns (df, snapshot_date).
    """
    rng = np.random.default_rng(seed)
    # Snapshot is the 1st of the month after YESTERDAY
    _snap_month = YESTERDAY.month % 12 + 1
    _snap_year = YESTERDAY.year + (1 if YESTERDAY.month == 12 else 0)
    snapshot = _dt.date(_snap_year, _snap_month, 1)
    days = np.arange(0, 1500)

    # Acquisition volume spread over Jan 2025 - May 2026 per FITB actuals.
    schedule = _fitb_monthly_open_schedule(rng)
    total = sum(c for _, _, c in schedule)

    # Base sBG survivor curves per ORIGINATION (the dominant retention driver).
    base = {
        "Branch": survival_sbg(days, 0.165, 62.0),   # e-coupon -> branch; MOB6 ~0.80
        "Online": survival_sbg(days, 0.245, 47.0),    # online complete; MOB6 ~0.70
    }
    cond = {}
    for k, s in base.items():
        c = np.ones_like(s)
        c[1:] = np.clip(s[1:] / np.clip(s[:-1], 1e-9, None), 0.0, 1.0)
        cond[k] = c

    channel_def = {
        "SEM": (0.70, {
            "Brand": (0.45, 0.85, 0.34),
            "Non-brand": (0.55, 1.08, 0.24),
        }),
        "SEO": (0.15, {
            "Brand-Transactional": (0.30, 0.82, 0.36),
            "Brand-Non-transactional": (0.20, 0.98, 0.30),
            "Non-brand-Transactional": (0.30, 1.05, 0.24),
            "Non-brand-Non-transactional": (0.20, 1.18, 0.18),
        }),
        "PMAX": (0.05, {
            "Brand": (0.35, 0.92, 0.30),
            "Non-brand": (0.65, 1.12, 0.22),
        }),
        "META": (0.05, {
            "FB-Financial Intent": (0.25, 0.95, 0.26),
            "IG-Financial Intent": (0.20, 0.98, 0.26),
            "FB-Retargeting": (0.20, 1.15, 0.20),
            "IG-Retargeting": (0.15, 1.18, 0.20),
            "Affluence": (0.20, 0.80, 0.30),
        }),
        "Other": (0.05, {
            "Email/CRM": (0.60, 0.90, 0.28),
            "Internal Traffic": (0.40, 0.85, 0.40),
        }),
    }
    device = {"iOS": 0.46, "Android": 0.40, "Web": 0.14}
    dev_mod = {"iOS": 0.97, "Android": 1.0, "Web": 1.12}

    def draw(dist):
        ks = list(dist)
        ps = np.array(list(dist.values()))
        ps = ps / ps.sum()
        return ks, ps

    ch_k, ch_p = draw({c: v[0] for c, v in channel_def.items()})
    dv_k, dv_p = draw(device)

    channel = rng.choice(ch_k, total, p=ch_p)
    device_t = rng.choice(dv_k, total, p=dv_p)

    audience = np.empty(total, dtype=object)
    aud_mod = np.ones(total)
    p_branch = np.zeros(total)
    for c, (_, auds) in channel_def.items():
        m = channel == c
        n = int(m.sum())
        if n == 0:
            continue
        a_k, a_p = draw({a: v[0] for a, v in auds.items()})
        picks = rng.choice(a_k, n, p=a_p)
        audience[m] = picks
        aud_mod[m] = np.array([auds[p][1] for p in picks])
        p_branch[m] = np.array([auds[p][2] for p in picks])

    orig = np.where(rng.random(total) < p_branch, "Branch", "Online")
    mod = aud_mod * np.array([dev_mod[d] for d in device_t])

    # Open dates assigned from the FITB monthly acquisition schedule
    open_dates = []
    for (yr, mo, cnt) in schedule:
        ndays = calendar.monthrange(yr, mo)[1]
        # For the snapshot month, only days strictly before the snapshot exist
        if (yr, mo) == (snapshot.year, snapshot.month):
            ndays = max(snapshot.day - 1, 1)
        day_choices = rng.integers(1, ndays + 1, size=cnt)
        open_dates.extend(_dt.date(yr, mo, int(d)) for d in day_choices)
    rng.shuffle(open_dates)

    close_dates = []
    cache = {}
    u_all = rng.random(total)
    for i in range(total):
        key = (orig[i], round(mod[i], 3))
        s_mod = cache.get(key)
        if s_mod is None:
            churn = np.clip(mod[i] * (1 - cond[orig[i]]), 0.0, 1.0)
            s_mod = np.cumprod(1 - churn)
            cache[key] = s_mod
        life = int(np.searchsorted(-s_mod, -u_all[i]))
        cd = open_dates[i] + _dt.timedelta(days=life)
        close_dates.append(None if cd >= snapshot else cd)

    df = pd.DataFrame({
        "ACCOUNT_OPEN_DATE": open_dates,
        "ACCOUNT_CLOSED_DATE": close_dates,
        "DEVICE_TYPE": device_t,
        "AUDIENCE": audience,
        "CHANNEL": channel,
        "ORIGINATION": orig,
    })
    return df, snapshot
