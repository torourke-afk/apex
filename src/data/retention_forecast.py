"""
Retention Forecast Data Layer
-----------------------------
Cached wrappers around the retention model for use by Streamlit pages.

Public API
----------
load_account_data()              → (DataFrame, date)  — synthetic accounts + snapshot
load_fits(segment_col)           → (seg_fits, pooled)  — fitted curves per segment
get_survival_curves(fits, ...)   → dict[str, np.array] — pre-computed S(t) arrays
get_retained_hh_estimate(...)    → dict                — portfolio retention for scorecard KPI
get_segment_options()            → dict                — available filter values
"""

from __future__ import annotations

import datetime as _dt

import numpy as np
import pandas as pd
import streamlit as st

from src.data.account_retention_core import (
    make_synthetic_accounts,
    fit_all_segments,
    compute_tenures,
    kaplan_meier,
    _effective_counts,
)
from src.data.retention_model_core import (
    SegmentFit,
    shrink_survival,
    retention_on_date,
    portfolio_retention_on_date,
)


# -----------------------------------------------------------------------------
# 1. Load and cache account data
# -----------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def load_account_data() -> tuple[pd.DataFrame, _dt.date]:
    """Load (or generate) the synthetic FITB account table. Cached 1 hour."""
    df, snapshot = make_synthetic_accounts(seed=7, total=250_000)
    return df, snapshot


# -----------------------------------------------------------------------------
# 2. Fit all segments — expensive, cached aggressively
# -----------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner="Fitting retention curves…", hash_funcs={pd.DataFrame: lambda df: hash(tuple(df.columns) + (len(df),))})
def _fit_segments_cached(df_pickle: bytes, segment_col: str, snapshot_str: str):
    """Internal: fits segments from serialized df. Caching wrapper."""
    import pickle
    df = pickle.loads(df_pickle)
    snapshot = _dt.date.fromisoformat(snapshot_str)
    seg_fits, pooled = fit_all_segments(
        df, [segment_col] if segment_col else None,
        snapshot=snapshot, verbose=False,
    )
    # Serialize fits for caching (SegmentFit contains callables, store as dicts)
    return seg_fits, pooled


def load_fits(segment_col: str = "ORIGINATION") -> tuple[dict[str, SegmentFit], SegmentFit]:
    """Load fitted segment curves. Returns (seg_fits, pooled_fit)."""
    import pickle
    df, snapshot = load_account_data()
    df_bytes = pickle.dumps(df)
    return _fit_segments_cached(df_bytes, segment_col, snapshot.isoformat())


# -----------------------------------------------------------------------------
# 3. Pre-compute survival curves for charting
# -----------------------------------------------------------------------------

def get_survival_curves(
    seg_fits: dict[str, SegmentFit],
    pooled_fit: SegmentFit,
    horizon_days: int = 940,
    tau: float = 500.0,
) -> dict[str, np.ndarray]:
    """Compute S(t) arrays for each segment + portfolio blend.

    Returns dict mapping segment name → np.array of shape (horizon_days+1,).
    Includes a "Portfolio (blended)" key with mix-weighted average.
    """
    t = np.arange(0, horizon_days + 1)
    curves = {}
    for name, sf in seg_fits.items():
        curves[name] = shrink_survival(t, sf, pooled_fit, tau)

    # Portfolio blend: weight by account count
    total_n = sum(sf.n0 for sf in seg_fits.values())
    if total_n > 0 and seg_fits:
        blend = np.zeros(horizon_days + 1)
        for name, sf in seg_fits.items():
            blend += (sf.n0 / total_n) * curves[name]
        curves["Portfolio (blended)"] = blend

    return curves


# -----------------------------------------------------------------------------
# 4. Segment filter options
# -----------------------------------------------------------------------------

def get_segment_options() -> dict[str, list[str]]:
    """Return available values for each segmentation column."""
    df, _ = load_account_data()
    return {
        "CHANNEL": sorted(df["CHANNEL"].unique().tolist()),
        "ORIGINATION": sorted(df["ORIGINATION"].unique().tolist()),
        "AUDIENCE": sorted(df["AUDIENCE"].unique().tolist()),
        "DEVICE_TYPE": sorted(df["DEVICE_TYPE"].unique().tolist()),
    }


# -----------------------------------------------------------------------------
# 5. Scorecard KPI helper
# -----------------------------------------------------------------------------

def get_retained_hh_estimate(horizon_days: int = 365) -> dict:
    """Return estimated retained households for the scorecard KPI card.

    Returns dict with keys: value, delta, delta_pct, sparkline_data, format_type.
    """
    df, snapshot = load_account_data()
    seg_fits, pooled = load_fits("ORIGINATION")

    # Total accounts in the dataset
    total_hh = len(df)

    # Portfolio retention at target horizon
    t = np.arange(0, horizon_days + 1)
    total_n = sum(sf.n0 for sf in seg_fits.values())
    if total_n > 0 and seg_fits:
        blend = np.zeros(horizon_days + 1)
        for name, sf in seg_fits.items():
            blend += (sf.n0 / total_n) * shrink_survival(t, sf, pooled)
        retention_rate = blend[horizon_days]
    else:
        retention_rate = pooled.survival_fn(np.array([horizon_days]), *pooled.raw_params)[0]

    retained_hh = int(total_hh * retention_rate)

    # Sparkline: retention at 30-day intervals over the last 12 periods
    sparkline = []
    for i in range(12):
        day = max(1, horizon_days - (11 - i) * 30)
        if total_n > 0 and seg_fits:
            r = blend[min(day, horizon_days)]
        else:
            r = float(pooled.survival_fn(np.array([day]), *pooled.raw_params)[0])
        sparkline.append(int(total_hh * r))

    # Delta: compare 365d retention vs 335d retention (last 30 days of decay)
    prev_day = max(1, horizon_days - 30)
    if total_n > 0 and seg_fits:
        prev_rate = blend[prev_day]
    else:
        prev_rate = float(pooled.survival_fn(np.array([prev_day]), *pooled.raw_params)[0])
    prev_hh = int(total_hh * prev_rate)
    delta = retained_hh - prev_hh
    delta_pct = ((retained_hh / prev_hh) - 1) * 100 if prev_hh else 0

    return {
        "name": "Est. Retained HH",
        "value": retained_hh,
        "delta": delta,
        "delta_pct": delta_pct,
        "sparkline_data": sparkline,
        "format_type": "number",
        "alert_status": "warning" if retention_rate < 0.65 else None,
    }


# -----------------------------------------------------------------------------
# 6. KM observed data for chart overlay
# -----------------------------------------------------------------------------

def get_km_observed(segment_col: str = "ORIGINATION") -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Return raw Kaplan-Meier curves per segment for chart overlay.

    Returns dict mapping segment name → (t_grid, S_km) arrays.
    """
    df, snapshot = load_account_data()
    df = compute_tenures(df, snapshot=snapshot)
    result = {}
    if segment_col:
        for key, grp in df.groupby(segment_col):
            name = key if isinstance(key, str) else " | ".join(map(str, key))
            t_grid, s_km = kaplan_meier(grp["tenure_days"].values, grp["is_closed"].values)
            result[name] = (t_grid, s_km)
    # Pooled
    t_grid, s_km = kaplan_meier(df["tenure_days"].values, df["is_closed"].values)
    result["POOLED"] = (t_grid, s_km)
    return result
