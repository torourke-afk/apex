"""
load_social.py
--------------
Synthetic data loaders for the Social channel analytics tab.

Three public functions:
  - load_social_overview()   → dict of KPI values for the 5-card strip
  - load_social_platforms()  → dict of per-platform metrics + spend shares
  - load_social_creatives()  → pd.DataFrame of creative-level performance

All data is seeded synthetic. Replace with real DB queries when available.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Constants — benchmarks live here so the page can reference them
# ---------------------------------------------------------------------------

BENCHMARKS = {
    "cpl_sem": 48.50,          # SEM CPL — social CPL should be below this
    "native_cvr": 13.0,        # Native lead form CVR benchmark (%)
    "lp_cvr": 4.02,            # Landing page CVR benchmark (%)
    "ai_cpa_vs_manual": -10.0, # AI CPA should be ≥10% below manual CPA (%)
    "fp_audiences": 15,        # First-party audiences benchmark (count)
}

ALERT_THRESHOLDS = {
    "cpl_sem": "above",        # alert when social CPL > SEM CPL (CPL > benchmark)
    "native_cvr": 10.0,        # alert if < 10%
    "lp_cvr": 3.0,             # alert if < 3%
    "ai_cpa_vs_manual": 0.0,   # alert if AI CPA delta ≥ 0% (not saving)
    "fp_audiences": 12,        # alert if < 12
}

_PLATFORMS = ["Meta", "TikTok", "LinkedIn", "Other"]
_PLATFORM_SPEND_SHARES = {"Meta": 0.70, "TikTok": 0.15, "LinkedIn": 0.10, "Other": 0.05}

_FORMATS = ["Video", "Static Image", "Carousel", "Story", "Reels", "Sponsored Post"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def load_social_overview() -> dict:
    """
    Return current-period KPI values for the Paid Social KPI strip.

    Returns
    -------
    dict with keys:
      cpl            – Current CPL for native lead forms (USD)
      native_cvr     – Native lead form CVR (%)
      lp_cvr         – Landing page CVR (%)
      ai_cpa         – AI-optimized CPA (USD)
      manual_cpa     – Manual CPA baseline (USD)
      fp_audiences   – Count of active first-party audiences
      cpl_delta      – Change vs prior period (USD)
      native_cvr_delta – Change vs prior period (pp)
      lp_cvr_delta   – Change vs prior period (pp)
      ai_cpa_delta   – Change vs prior period (USD)
    """
    rng = np.random.default_rng(42)

    # Current values (slightly worse than benchmarks to trigger some alerts)
    cpl = round(rng.uniform(44.0, 52.0), 2)           # May straddle SEM CPL
    native_cvr = round(rng.uniform(8.5, 14.5), 1)     # May fall below 10% threshold
    lp_cvr = round(rng.uniform(2.8, 4.8), 2)          # May fall below 3% threshold
    manual_cpa = round(rng.uniform(85.0, 105.0), 2)
    ai_cpa = round(manual_cpa * rng.uniform(0.85, 1.02), 2)  # Sometimes above manual
    fp_audiences = int(rng.integers(10, 20))           # May fall below 12

    # Deltas vs prior period
    cpl_delta = round(rng.uniform(-4.0, 3.0), 2)
    native_cvr_delta = round(rng.uniform(-2.0, 2.0), 1)
    lp_cvr_delta = round(rng.uniform(-0.5, 0.5), 2)
    ai_cpa_delta = round(rng.uniform(-8.0, 4.0), 2)

    return {
        "cpl": cpl,
        "native_cvr": native_cvr,
        "lp_cvr": lp_cvr,
        "ai_cpa": ai_cpa,
        "manual_cpa": manual_cpa,
        "fp_audiences": fp_audiences,
        "cpl_delta": cpl_delta,
        "native_cvr_delta": native_cvr_delta,
        "lp_cvr_delta": lp_cvr_delta,
        "ai_cpa_delta": ai_cpa_delta,
    }


@st.cache_data(ttl=300)
def load_social_platforms() -> dict:
    """
    Return per-platform performance metrics and spend shares.

    Returns
    -------
    dict keyed by platform name ("Meta", "TikTok", "LinkedIn", "Other"):
      Each value is a dict with:
        spend        – Total spend this period (USD)
        spend_share  – Share of total social spend (0–1)
        cpl          – Cost per lead (USD)
        cvr          – Conversion rate (%)
        volume       – Lead volume (count)
    Also includes:
      total_spend    – Aggregate social spend
    """
    rng = np.random.default_rng(7)
    total_spend = rng.uniform(180_000, 240_000)

    platforms: dict[str, dict] = {}
    for platform in _PLATFORMS:
        share = _PLATFORM_SPEND_SHARES[platform]
        spend = total_spend * share

        # Platform-specific performance ranges
        if platform == "Meta":
            cpl = rng.uniform(38.0, 50.0)
            cvr = rng.uniform(11.0, 15.0)
        elif platform == "TikTok":
            cpl = rng.uniform(30.0, 45.0)
            cvr = rng.uniform(9.0, 13.0)
        elif platform == "LinkedIn":
            cpl = rng.uniform(65.0, 95.0)
            cvr = rng.uniform(6.0, 10.0)
        else:
            cpl = rng.uniform(42.0, 60.0)
            cvr = rng.uniform(8.0, 12.0)

        volume = int(spend / cpl)

        platforms[platform] = {
            "spend": round(float(spend), 2),
            "spend_share": share,
            "cpl": round(float(cpl), 2),
            "cvr": round(float(cvr), 1),
            "volume": volume,
        }

    platforms["total_spend"] = round(float(total_spend), 2)
    return platforms


@st.cache_data(ttl=300)
def load_social_creatives() -> pd.DataFrame:
    """
    Return creative-level performance data for the sortable creative table.

    Returns
    -------
    pd.DataFrame with columns:
      Creative Name, Platform, Format, CTR, CVR, Spend, Impressions

    Rows with CTR < 1.0% or CVR < 5.0% are flagged as underperformers
    via an ``underperformer`` boolean column.
    """
    rng = np.random.default_rng(99)
    n = 20

    platforms_pool = rng.choice(_PLATFORMS, size=n, p=[0.70, 0.15, 0.10, 0.05])
    formats_pool = rng.choice(_FORMATS, size=n)

    rows = []
    for i in range(n):
        platform = platforms_pool[i]
        fmt = formats_pool[i]

        # Generate performance with some intentional underperformers
        ctr = round(float(rng.uniform(0.4, 3.5)), 2)
        cvr = round(float(rng.uniform(3.0, 18.0)), 1)
        impressions = int(rng.integers(50_000, 2_000_000))
        spend = round(float(rng.uniform(2_000, 45_000)), 2)

        name = f"{platform}-{fmt.replace(' ', '')}-{i + 1:02d}"

        rows.append(
            {
                "Creative Name": name,
                "Platform": platform,
                "Format": fmt,
                "CTR": ctr,
                "CVR": cvr,
                "Spend": spend,
                "Impressions": impressions,
                "underperformer": ctr < 1.0 or cvr < 5.0,
            }
        )

    df = pd.DataFrame(rows).sort_values("CTR", ascending=False).reset_index(drop=True)
    return df
