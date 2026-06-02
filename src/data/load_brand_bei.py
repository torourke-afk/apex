"""
Brand Equity Index (BEI) Data Loader — APE-81 / APE-87
-------------------------------------------------------
Provides BEI score components and 12-week trend data per market.

BEI formula:
    BEI = (0.25 × Awareness) + (0.25 × Branded Search)
        + (0.20 × Direct Traffic) + (0.20 × Branch Visits)
        + (0.10 × Social Engagement)

Falls back to embedded synthetic data when the database table is
missing or empty, so the page renders in all environments.

Columns returned by ``load_brand_bei()``:
    dma             str    DMA name
    state           str    State abbreviation
    tier            int    1 / 2 / 3
    awareness       float  0–100 awareness score
    branded_search  float  0–100 branded search index
    direct_traffic  float  0–100 direct-traffic index
    branch_visits   float  0–100 branch-visit index
    social_eng      float  0–100 social-engagement index
    bei             float  0–100 composite BEI score

``load_brand_frequency()`` adds:
    freq_compliance  float  % of growth markets at effective reach threshold
    ctv_completion   float  CTV completion rate %
    olv_completion   float  OLV completion rate %
    audio_ltr        float  Streaming audio listen-through rate %
    incrementality   float  Active-vs-control lift delta (pp)
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# BEI weights (per spec)
# ---------------------------------------------------------------------------

BEI_WEIGHTS: dict[str, float] = {
    "awareness":       0.25,
    "branded_search":  0.25,
    "direct_traffic":  0.20,
    "branch_visits":   0.20,
    "social_eng":      0.10,
}


def _compute_bei(row: dict[str, float]) -> float:
    return round(
        BEI_WEIGHTS["awareness"]      * row["awareness"]
        + BEI_WEIGHTS["branded_search"] * row["branded_search"]
        + BEI_WEIGHTS["direct_traffic"] * row["direct_traffic"]
        + BEI_WEIGHTS["branch_visits"]  * row["branch_visits"]
        + BEI_WEIGHTS["social_eng"]     * row["social_eng"],
        1,
    )


# ---------------------------------------------------------------------------
# Mock BEI market data — 20 DMAs, Tiers 1/2/3
# ---------------------------------------------------------------------------

_MOCK_BEI: list[dict[str, Any]] = [
    # Tier 1
    {"dma": "New York",      "state": "NY", "tier": 1, "awareness": 78, "branded_search": 74, "direct_traffic": 71, "branch_visits": 69, "social_eng": 65},
    {"dma": "Los Angeles",   "state": "CA", "tier": 1, "awareness": 72, "branded_search": 68, "direct_traffic": 65, "branch_visits": 63, "social_eng": 61},
    {"dma": "Chicago",       "state": "IL", "tier": 1, "awareness": 80, "branded_search": 77, "direct_traffic": 74, "branch_visits": 72, "social_eng": 70},
    {"dma": "Philadelphia",  "state": "PA", "tier": 1, "awareness": 73, "branded_search": 70, "direct_traffic": 67, "branch_visits": 65, "social_eng": 62},
    {"dma": "Dallas",        "state": "TX", "tier": 1, "awareness": 76, "branded_search": 72, "direct_traffic": 69, "branch_visits": 68, "social_eng": 66},
    {"dma": "Atlanta",       "state": "GA", "tier": 1, "awareness": 69, "branded_search": 65, "direct_traffic": 62, "branch_visits": 60, "social_eng": 58},
    {"dma": "Boston",        "state": "MA", "tier": 1, "awareness": 82, "branded_search": 79, "direct_traffic": 76, "branch_visits": 75, "social_eng": 73},
    {"dma": "Washington DC", "state": "DC", "tier": 1, "awareness": 79, "branded_search": 76, "direct_traffic": 73, "branch_visits": 71, "social_eng": 69},
    {"dma": "Houston",       "state": "TX", "tier": 1, "awareness": 70, "branded_search": 66, "direct_traffic": 63, "branch_visits": 62, "social_eng": 59},
    {"dma": "Phoenix",       "state": "AZ", "tier": 1, "awareness": 67, "branded_search": 63, "direct_traffic": 60, "branch_visits": 58, "social_eng": 56},
    # Tier 2
    {"dma": "Minneapolis",   "state": "MN", "tier": 2, "awareness": 75, "branded_search": 71, "direct_traffic": 68, "branch_visits": 67, "social_eng": 64},
    {"dma": "Detroit",       "state": "MI", "tier": 2, "awareness": 64, "branded_search": 60, "direct_traffic": 57, "branch_visits": 55, "social_eng": 53},
    {"dma": "Tampa",         "state": "FL", "tier": 2, "awareness": 66, "branded_search": 62, "direct_traffic": 59, "branch_visits": 58, "social_eng": 55},
    {"dma": "Seattle",       "state": "WA", "tier": 2, "awareness": 74, "branded_search": 70, "direct_traffic": 67, "branch_visits": 65, "social_eng": 63},
    {"dma": "Denver",        "state": "CO", "tier": 2, "awareness": 71, "branded_search": 67, "direct_traffic": 64, "branch_visits": 63, "social_eng": 60},
    {"dma": "St. Louis",     "state": "MO", "tier": 2, "awareness": 68, "branded_search": 64, "direct_traffic": 61, "branch_visits": 59, "social_eng": 57},
    {"dma": "Baltimore",     "state": "MD", "tier": 2, "awareness": 65, "branded_search": 61, "direct_traffic": 58, "branch_visits": 56, "social_eng": 54},
    # Tier 3
    {"dma": "Cincinnati",    "state": "OH", "tier": 3, "awareness": 62, "branded_search": 58, "direct_traffic": 55, "branch_visits": 53, "social_eng": 51},
    {"dma": "Kansas City",   "state": "MO", "tier": 3, "awareness": 59, "branded_search": 55, "direct_traffic": 52, "branch_visits": 50, "social_eng": 48},
    {"dma": "Indianapolis",  "state": "IN", "tier": 3, "awareness": 57, "branded_search": 53, "direct_traffic": 50, "branch_visits": 48, "social_eng": 46},
]


def _add_bei(records: list[dict]) -> list[dict]:
    for row in records:
        row["bei"] = _compute_bei(row)
    return records


# ---------------------------------------------------------------------------
# 12-week BEI trend data
# ---------------------------------------------------------------------------

def _make_week_dates(n: int = 12) -> list[str]:
    today = date.today()
    last_sunday = today - timedelta(days=(today.weekday() + 1) % 7)
    return [
        (last_sunday - timedelta(weeks=n - 1 - i)).isoformat()
        for i in range(n)
    ]


def _generate_trend(base_bei: float, dma: str, n: int = 12) -> list[dict]:
    """Simulate a 12-week BEI trend for a given market."""
    rng = random.Random(hash(dma) & 0xFFFF)
    weeks = _make_week_dates(n)
    current = base_bei - rng.uniform(3, 6)
    rows = []
    for week in weeks:
        current += rng.uniform(-1.2, 1.8)
        current = max(30.0, min(99.0, current))
        rows.append({"week_ending": week, "bei": round(current, 1)})
    # anchor last point near true BEI
    rows[-1]["bei"] = round(base_bei + rng.uniform(-0.5, 0.5), 1)
    return rows


# ---------------------------------------------------------------------------
# Public loaders
# ---------------------------------------------------------------------------

def load_brand_bei() -> pd.DataFrame:
    """
    Return a DataFrame of BEI scores per market.

    Tries the live ``brand_bei`` table first; falls back to embedded mock data
    when unavailable.

    Returns
    -------
    pd.DataFrame with columns:
        dma, state, tier, awareness, branded_search, direct_traffic,
        branch_visits, social_eng, bei
    """
    try:
        from src.data.init_db import get_connection
        conn = get_connection()
        df = conn.execute(
            """
            SELECT dma, state, tier,
                   awareness, branded_search, direct_traffic,
                   branch_visits, social_eng, bei
            FROM brand_bei
            ORDER BY tier, bei DESC
            """
        ).df()
        conn.close()
        if not df.empty:
            return df
    except Exception:
        pass

    records = [dict(r) for r in _MOCK_BEI]
    records = _add_bei(records)
    return pd.DataFrame(records).sort_values(["tier", "bei"], ascending=[True, False]).reset_index(drop=True)


def load_brand_bei_trend() -> pd.DataFrame:
    """
    Return a 12-week BEI trend DataFrame.

    Columns: dma, state, tier, week_ending (str ISO date), bei (float)
    """
    df = load_brand_bei()
    rows = []
    for _, row in df.iterrows():
        trend = _generate_trend(row["bei"], row["dma"])
        for pt in trend:
            rows.append({
                "dma":         row["dma"],
                "state":       row["state"],
                "tier":        row["tier"],
                "week_ending": pt["week_ending"],
                "bei":         pt["bei"],
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Mock frequency / media metrics
# ---------------------------------------------------------------------------

_MOCK_FREQUENCY: dict[str, float] = {
    "freq_compliance":  71.4,   # % of growth markets at effective reach threshold
    "ctv_completion":   88.2,   # CTV video completion rate %
    "olv_completion":   82.7,   # OLV video completion rate %
    "audio_ltr":        76.5,   # Streaming audio listen-through rate %
    "incrementality":   +4.3,   # Active vs control market lift delta (pp)
}


def load_brand_frequency() -> dict[str, float]:
    """
    Return brand media frequency and completion metrics.

    Tries ``brand_frequency`` table; falls back to embedded mock values.

    Returns
    -------
    dict with keys:
        freq_compliance, ctv_completion, olv_completion, audio_ltr, incrementality
    """
    try:
        from src.data.init_db import get_connection
        conn = get_connection()
        row = conn.execute(
            """
            SELECT freq_compliance, ctv_completion, olv_completion,
                   audio_ltr, incrementality
            FROM brand_frequency
            ORDER BY created_at DESC
            LIMIT 1
            """
        ).fetchone()
        conn.close()
        if row:
            keys = ["freq_compliance", "ctv_completion", "olv_completion", "audio_ltr", "incrementality"]
            return dict(zip(keys, row))
    except Exception:
        pass

    return dict(_MOCK_FREQUENCY)
