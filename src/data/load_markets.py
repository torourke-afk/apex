"""
Markets Data Module — APE-65
-----------------------------
Loads DMA market data from the database (markets table seeded by APE-62).
Falls back to embedded mock data when the table is not yet populated,
so the page renders in all environments without a seed run.

Columns returned:
    dma         str   DMA name (e.g. "New York")
    state       str   Primary state abbreviation for geo mapping
    tier        int   1 / 2 / 3
    spend       float Monthly media spend ($)
    brand_health float 0–100 brand health index
    retention   float MOB6 retention rate (0–100)
    cpihh       float Cost per incremental household ($)
    nps         float Net Promoter Score (-100 to 100)
    ltv         float Estimated customer LTV ($)
    sparkline   list  12-point brand health time series
"""

from __future__ import annotations

import json
import random
from typing import Any

import pandas as pd

from src.data.init_db import get_connection

# ---------------------------------------------------------------------------
# Mock dataset — 20 DMAs covering Tier 1/2/3 distribution per APE-62 spec
# ---------------------------------------------------------------------------
_MOCK_MARKETS: list[dict[str, Any]] = [
    # Tier 1 — 10 DMAs
    {"dma": "New York",       "state": "NY", "tier": 1, "spend": 1_420_000, "brand_health": 72.4, "retention": 86.2, "cpihh": 295, "nps": 41, "ltv": 3_820},
    {"dma": "Los Angeles",    "state": "CA", "tier": 1, "spend": 1_185_000, "brand_health": 68.1, "retention": 83.7, "cpihh": 318, "nps": 37, "ltv": 3_650},
    {"dma": "Chicago",        "state": "IL", "tier": 1, "spend":   980_000, "brand_health": 74.8, "retention": 87.4, "cpihh": 278, "nps": 45, "ltv": 3_940},
    {"dma": "Philadelphia",   "state": "PA", "tier": 1, "spend":   840_000, "brand_health": 69.3, "retention": 84.9, "cpihh": 302, "nps": 39, "ltv": 3_710},
    {"dma": "Dallas",         "state": "TX", "tier": 1, "spend":   790_000, "brand_health": 71.5, "retention": 85.6, "cpihh": 289, "nps": 43, "ltv": 3_780},
    {"dma": "Atlanta",        "state": "GA", "tier": 1, "spend":   720_000, "brand_health": 66.9, "retention": 82.1, "cpihh": 331, "nps": 34, "ltv": 3_510},
    {"dma": "Boston",         "state": "MA", "tier": 1, "spend":   680_000, "brand_health": 76.2, "retention": 88.3, "cpihh": 265, "nps": 48, "ltv": 4_020},
    {"dma": "Washington DC",  "state": "DC", "tier": 1, "spend":   650_000, "brand_health": 73.7, "retention": 86.8, "cpihh": 281, "nps": 44, "ltv": 3_890},
    {"dma": "Houston",        "state": "TX", "tier": 1, "spend":   620_000, "brand_health": 67.4, "retention": 83.2, "cpihh": 322, "nps": 36, "ltv": 3_580},
    {"dma": "Phoenix",        "state": "AZ", "tier": 1, "spend":   590_000, "brand_health": 64.8, "retention": 81.5, "cpihh": 342, "nps": 31, "ltv": 3_430},
    # Tier 2 — 7 DMAs
    {"dma": "Minneapolis",    "state": "MN", "tier": 2, "spend":   380_000, "brand_health": 71.1, "retention": 85.0, "cpihh": 298, "nps": 42, "ltv": 3_740},
    {"dma": "Detroit",        "state": "MI", "tier": 2, "spend":   350_000, "brand_health": 63.5, "retention": 80.4, "cpihh": 358, "nps": 28, "ltv": 3_320},
    {"dma": "Tampa",          "state": "FL", "tier": 2, "spend":   320_000, "brand_health": 65.9, "retention": 81.9, "cpihh": 338, "nps": 33, "ltv": 3_480},
    {"dma": "Seattle",        "state": "WA", "tier": 2, "spend":   310_000, "brand_health": 70.4, "retention": 84.2, "cpihh": 308, "nps": 40, "ltv": 3_660},
    {"dma": "Denver",         "state": "CO", "tier": 2, "spend":   295_000, "brand_health": 68.7, "retention": 83.5, "cpihh": 315, "nps": 38, "ltv": 3_620},
    {"dma": "St. Louis",      "state": "MO", "tier": 2, "spend":   270_000, "brand_health": 66.2, "retention": 82.3, "cpihh": 328, "nps": 35, "ltv": 3_540},
    {"dma": "Baltimore",      "state": "MD", "tier": 2, "spend":   255_000, "brand_health": 64.4, "retention": 81.1, "cpihh": 345, "nps": 30, "ltv": 3_390},
    # Tier 3 — 3 DMAs
    {"dma": "Cincinnati",     "state": "OH", "tier": 3, "spend":   145_000, "brand_health": 61.8, "retention": 79.7, "cpihh": 372, "nps": 24, "ltv": 3_180},
    {"dma": "Kansas City",    "state": "MO", "tier": 3, "spend":   130_000, "brand_health": 59.3, "retention": 78.2, "cpihh": 391, "nps": 20, "ltv": 3_050},
    {"dma": "Indianapolis",   "state": "IN", "tier": 3, "spend":   118_000, "brand_health": 57.6, "retention": 77.0, "cpihh": 408, "nps": 17, "ltv": 2_940},
]


def _add_sparklines(records: list[dict]) -> list[dict]:
    """Generate a 12-month brand health sparkline for each record."""
    rng = random.Random(42)
    for row in records:
        base = row["brand_health"]
        points: list[float] = []
        cur = base - rng.uniform(4, 8)
        for _ in range(12):
            cur += rng.uniform(-1.5, 2.2)
            cur = max(30.0, min(99.0, cur))
            points.append(round(cur, 1))
        # Ensure last point near current value
        points[-1] = round(base + rng.uniform(-0.5, 0.5), 1)
        row["sparkline"] = points
    return records


def _load_from_db() -> pd.DataFrame | None:
    """Return DataFrame from the markets table, or None if unavailable."""
    try:
        conn = get_connection()
        df = conn.execute(
            """
            SELECT dma, state, tier, spend, brand_health, retention, cpihh, nps, ltv
            FROM markets
            ORDER BY tier, spend DESC
            """
        ).df()
        conn.close()
        if df.empty:
            return None
        return df
    except Exception:
        return None


@pd.api.extensions.register_dataframe_accessor("_apex_markets_tag")
class _Noop:
    """No-op accessor — keeps the module importable as a side-effect check."""
    def __init__(self, df):  # noqa: D107
        pass


def load_markets() -> pd.DataFrame:
    """
    Return a DataFrame of DMA market data.

    Tries the live ``markets`` table first; falls back to embedded mock data
    if the table is missing or empty. Always returns a ``sparkline`` column
    (list of 12 floats) suitable for inline chart rendering.

    Returns
    -------
    pd.DataFrame with columns:
        dma, state, tier, spend, brand_health, retention, cpihh, nps, ltv, sparkline
    """
    df = _load_from_db()
    if df is not None:
        # Attach sparklines if not already persisted in DB
        if "sparkline" not in df.columns:
            records = df.to_dict("records")
            records = _add_sparklines(records)
            df = pd.DataFrame(records)
        return df

    # Fallback: in-memory mock
    records = [dict(row) for row in _MOCK_MARKETS]
    records = _add_sparklines(records)
    return pd.DataFrame(records)


def tier_budget_impact(
    df: pd.DataFrame,
    dma: str,
    new_tier: int,
    *,
    tier_multipliers: dict[int, float] | None = None,
) -> dict[str, float]:
    """
    Estimate budget impact of reassigning a DMA to a different tier.

    Parameters
    ----------
    df : pd.DataFrame
        Full markets DataFrame from ``load_markets()``.
    dma : str
        DMA name to reassign.
    new_tier : int
        Target tier (1, 2, or 3).
    tier_multipliers : dict, optional
        Per-tier spend multiplier relative to Tier 1 baseline.
        Default: {1: 1.0, 2: 0.45, 3: 0.18}

    Returns
    -------
    dict with keys:
        current_spend, projected_spend, delta, delta_pct, current_tier, new_tier
    """
    if tier_multipliers is None:
        tier_multipliers = {1: 1.0, 2: 0.45, 3: 0.18}

    row = df[df["dma"] == dma]
    if row.empty:
        raise ValueError(f"DMA not found: {dma}")

    row = row.iloc[0]
    current_tier = int(row["tier"])
    current_spend = float(row["spend"])

    # Estimate spend for the new tier using the ratio of multipliers
    ratio = tier_multipliers[new_tier] / tier_multipliers[current_tier]
    projected_spend = current_spend * ratio
    delta = projected_spend - current_spend

    return {
        "current_tier": current_tier,
        "new_tier": new_tier,
        "current_spend": current_spend,
        "projected_spend": projected_spend,
        "delta": delta,
        "delta_pct": (delta / current_spend) * 100 if current_spend else 0.0,
    }
