"""
Day-0 Retention Forecasting Model
=================================

Fits a discrete-time retention (survival) curve to historical daily cohort data
and projects the probability that a customer acquired on day 0 is still retained
on any future calendar date.

Three competing curve families are fit per segment and the best is chosen by
held-out (out-of-sample) error:

    1. sBG   - shifted Beta-Geometric (Fader & Hardie). Heterogeneous discrete
               churn. Industry standard for "contractual" retention.
    2. Weibull - discrete-time Weibull survival. Flexible decay shape.
    3. 2-exp - two-segment ("leavers vs. stayers") exponential mixture.

Segments are modeled discretely: each segment gets its own fitted parameters.
Thin segments are stabilized by shrinking toward the pooled (all-data) fit.

A portfolio forecast for a future date is the mix-weighted blend of segment
curves.

Adapted from the standalone retention_model.py for Apex integration.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
from scipy.optimize import minimize


# -----------------------------------------------------------------------------
# 1. Retention curve families
# -----------------------------------------------------------------------------

def survival_sbg(t: np.ndarray, alpha: float, beta: float) -> np.ndarray:
    """Shifted Beta-Geometric survivor function."""
    t = np.asarray(t, dtype=float)
    t_max = int(np.max(t)) if t.size else 0
    s = np.ones(t_max + 1)
    for j in range(1, t_max + 1):
        s[j] = s[j - 1] * (beta + j - 1) / (alpha + beta + j - 1)
    return s[t.astype(int)]


def survival_weibull(t: np.ndarray, lam: float, k: float) -> np.ndarray:
    """Discrete-time Weibull survivor: S(t) = exp(-(lam * t) ** k)."""
    t = np.asarray(t, dtype=float)
    return np.exp(-((lam * t) ** k))


def survival_two_exp(t: np.ndarray, w: float, d_fast: float, d_slow: float) -> np.ndarray:
    """Two-segment exponential mixture."""
    t = np.asarray(t, dtype=float)
    return w * (d_fast ** t) + (1.0 - w) * (d_slow ** t)


@dataclass
class CurveSpec:
    name: str
    survival: Callable[..., np.ndarray]
    param_names: list[str]
    x0: list[float]
    bounds: list[tuple[float, float]]


def _curve_specs() -> dict[str, CurveSpec]:
    eps = 1e-6
    return {
        "sBG": CurveSpec(
            "sBG", survival_sbg, ["alpha", "beta"],
            x0=[1.0, 5.0],
            bounds=[(eps, 100.0), (eps, 1000.0)],
        ),
        "Weibull": CurveSpec(
            "Weibull", survival_weibull, ["lambda", "k"],
            x0=[0.05, 0.6],
            bounds=[(eps, 10.0), (eps, 5.0)],
        ),
        "2-exp": CurveSpec(
            "2-exp", survival_two_exp, ["w", "d_fast", "d_slow"],
            x0=[0.5, 0.8, 0.999],
            bounds=[(0.0, 1.0), (eps, 1 - eps), (eps, 1 - eps)],
        ),
    }


# -----------------------------------------------------------------------------
# 2. Likelihood / loss
# -----------------------------------------------------------------------------

def neg_log_likelihood(params, spec: CurveSpec, t_obs: np.ndarray,
                       n_obs: np.ndarray, n0: float) -> float:
    t_max = int(t_obs.max())
    full_t = np.arange(0, t_max + 1)
    s = spec.survival(full_t, *params)
    s = np.clip(s, 1e-12, 1.0)

    ll = 0.0
    prev_t, prev_n = 0, n0
    for t, n in zip(t_obs, n_obs):
        ti = int(t)
        if ti == 0:
            prev_t, prev_n = 0, n
            continue
        churned = prev_n - n
        p_interval = s[int(prev_t)] - s[ti]
        p_interval = max(p_interval, 1e-12)
        if churned > 0:
            ll += churned * np.log(p_interval)
        prev_t, prev_n = ti, n
    ll += prev_n * np.log(s[int(prev_t)])
    return -ll


def fit_curve(spec: CurveSpec, t_obs, n_obs, n0):
    res = minimize(
        neg_log_likelihood, spec.x0, args=(spec, t_obs, n_obs, n0),
        method="L-BFGS-B", bounds=spec.bounds,
    )
    return res.x, res.fun


# -----------------------------------------------------------------------------
# 3. Model selection on held-out days
# -----------------------------------------------------------------------------

@dataclass
class SegmentFit:
    segment: str
    best_model: str
    params: dict
    survival_fn: Callable
    raw_params: np.ndarray
    holdout_mae: dict
    n0: float


def fit_segment(t_obs: np.ndarray, n_obs: np.ndarray, segment: str = "ALL",
                holdout_frac: float = 0.3, verbose: bool = False) -> SegmentFit:
    t_obs = np.asarray(t_obs, float)
    n_obs = np.asarray(n_obs, float)
    n0 = n_obs[0]
    obs_ret = n_obs / n0

    split_t = t_obs[int(len(t_obs) * (1 - holdout_frac))]
    train_mask = t_obs <= split_t

    specs = _curve_specs()
    mae = {}
    fits = {}
    for name, spec in specs.items():
        p, _ = fit_curve(spec, t_obs[train_mask], n_obs[train_mask], n0)
        s_pred = spec.survival(t_obs[~train_mask], *p)
        mae[name] = float(np.mean(np.abs(s_pred - obs_ret[~train_mask]))) if (~train_mask).any() else np.nan
        fits[name] = (spec, p)

    best = min(mae, key=mae.get)
    spec = specs[best]
    p_full, _ = fit_curve(spec, t_obs, n_obs, n0)

    return SegmentFit(
        segment=segment, best_model=best,
        params=dict(zip(spec.param_names, p_full)),
        survival_fn=spec.survival, raw_params=p_full,
        holdout_mae=mae, n0=n0,
    )


# -----------------------------------------------------------------------------
# 4. Shrinkage for thin segments
# -----------------------------------------------------------------------------

def shrink_survival(t, seg_fit: SegmentFit, pooled_fit: SegmentFit,
                    tau: float = 500.0) -> np.ndarray:
    lam_w = seg_fit.n0 / (seg_fit.n0 + tau)
    s_seg = seg_fit.survival_fn(t, *seg_fit.raw_params)
    s_pool = pooled_fit.survival_fn(t, *pooled_fit.raw_params)
    return lam_w * s_seg + (1 - lam_w) * s_pool


# -----------------------------------------------------------------------------
# 5. Forecast to a future calendar date
# -----------------------------------------------------------------------------

def retention_on_date(acquisition_date: _dt.date, target_date: _dt.date,
                      seg_fit: SegmentFit, pooled_fit: SegmentFit | None = None,
                      tau: float = 500.0) -> float:
    horizon = (target_date - acquisition_date).days
    if horizon < 0:
        raise ValueError("target_date is before acquisition_date")
    if pooled_fit is not None:
        return float(shrink_survival(np.array([horizon]), seg_fit, pooled_fit, tau)[0])
    return float(seg_fit.survival_fn(np.array([horizon]), *seg_fit.raw_params)[0])


def portfolio_retention_on_date(acquisition_date, target_date,
                                seg_fits: dict, mix: dict,
                                pooled_fit: SegmentFit, tau: float = 500.0) -> float:
    total = sum(mix.values())
    r = 0.0
    for seg, share in mix.items():
        r += (share / total) * retention_on_date(
            acquisition_date, target_date, seg_fits[seg], pooled_fit, tau)
    return r
