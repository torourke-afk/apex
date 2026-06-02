"""
Life Events & Mover Marketing Data Loaders — APE-81
----------------------------------------------------
Provides mock-backed data for:
  - 8 always-on life event campaigns
  - Mover marketing pipeline and geo expansion table

Falls back to embedded mock data when the database tables are not yet
populated, so pages render in all environments without a seed run.

Public API
----------
load_life_events() → list[dict]
    One dict per campaign with CVR metrics and segment info.

load_movers() → dict
    "summary": dict of top-line mover metrics
    "geo_table": pd.DataFrame of geographic pipeline rows
"""

from __future__ import annotations

import pandas as pd

from src.data.init_db import get_connection

# ---------------------------------------------------------------------------
# Life Event Campaigns — 8 always-on campaigns
# ---------------------------------------------------------------------------

_LIFE_EVENT_MOCK: list[dict] = [
    {
        "name": "Home Purchase",
        "status": "active",
        "cvr": 4.8,
        "mass_market_cvr": 1.9,
        "cvr_multiplier": 2.53,
        "segment_size": 142_000,
        "key_params": "Pre-approval intent, 60-90 day window, income >$75K",
    },
    {
        "name": "Marriage",
        "status": "active",
        "cvr": 3.9,
        "mass_market_cvr": 1.9,
        "cvr_multiplier": 2.05,
        "segment_size": 88_500,
        "key_params": "Joint account signals, wedding registry cross-match, 6-mo window",
    },
    {
        "name": "New Child",
        "status": "active",
        "cvr": 4.2,
        "mass_market_cvr": 1.9,
        "cvr_multiplier": 2.21,
        "segment_size": 113_000,
        "key_params": "Baby registry, pediatric health searches, savings account propensity",
    },
    {
        "name": "College",
        "status": "active",
        "cvr": 3.1,
        "mass_market_cvr": 1.9,
        "cvr_multiplier": 1.63,
        "segment_size": 97_200,
        "key_params": "FAFSA trigger, 529 intent, 17-18 yr household signal",
    },
    {
        "name": "Inheritance",
        "status": "active",
        "cvr": 5.6,
        "mass_market_cvr": 1.9,
        "cvr_multiplier": 2.95,
        "segment_size": 31_800,
        "key_params": "Probate filing signal, wealth management trigger, high-value HH",
    },
    {
        "name": "Job Change",
        "status": "active",
        "cvr": 3.4,
        "mass_market_cvr": 1.9,
        "cvr_multiplier": 1.79,
        "segment_size": 204_000,
        "key_params": "LinkedIn employment change, 401k rollover intent, checking switch",
    },
    {
        "name": "Divorce",
        "status": "paused",
        "cvr": 2.7,
        "mass_market_cvr": 1.9,
        "cvr_multiplier": 1.42,
        "segment_size": 44_300,
        "key_params": "Account separation signals, solo checking intent, legal filing proxy",
    },
    {
        "name": "Retirement",
        "status": "active",
        "cvr": 4.4,
        "mass_market_cvr": 1.9,
        "cvr_multiplier": 2.32,
        "segment_size": 78_600,
        "key_params": "Age 62-67, Social Security filing, IRA/401k drawdown signals",
    },
]

# ---------------------------------------------------------------------------
# Mover Marketing — pipeline summary + geo expansion table
# ---------------------------------------------------------------------------

_MOVERS_SUMMARY: dict = {
    "total_pipeline_volume": 387_400,
    "avg_quality_score": 72.4,
    "blended_mover_cvr": 6.8,
    "propensity_benchmark": 4.1,  # x mass market CVR
}

_MOVERS_GEO_MOCK: list[dict] = [
    {
        "geo": "New York Metro",
        "pipeline_volume": 58_200,
        "quality_score": 74.8,
        "mover_cvr": 7.4,
        "benchmark": 6.1,
        "expansion_status": "Core",
        "high_income_cvr": 11.2,
        "high_income_volume": 14_800,
    },
    {
        "geo": "Los Angeles",
        "pipeline_volume": 49_100,
        "quality_score": 71.2,
        "mover_cvr": 6.9,
        "benchmark": 6.1,
        "expansion_status": "Core",
        "high_income_cvr": 10.4,
        "high_income_volume": 11_200,
    },
    {
        "geo": "Chicago",
        "pipeline_volume": 41_700,
        "quality_score": 73.6,
        "mover_cvr": 7.1,
        "benchmark": 6.1,
        "expansion_status": "Core",
        "high_income_cvr": 10.9,
        "high_income_volume": 9_800,
    },
    {
        "geo": "Dallas–Fort Worth",
        "pipeline_volume": 38_400,
        "quality_score": 75.3,
        "mover_cvr": 7.8,
        "benchmark": 6.1,
        "expansion_status": "Expanding",
        "high_income_cvr": 12.1,
        "high_income_volume": 8_900,
    },
    {
        "geo": "Phoenix",
        "pipeline_volume": 34_200,
        "quality_score": 76.1,
        "mover_cvr": 8.2,
        "benchmark": 6.1,
        "expansion_status": "Expanding",
        "high_income_cvr": 11.8,
        "high_income_volume": 7_400,
    },
    {
        "geo": "Atlanta",
        "pipeline_volume": 31_800,
        "quality_score": 72.9,
        "mover_cvr": 7.0,
        "benchmark": 6.1,
        "expansion_status": "Core",
        "high_income_cvr": 10.2,
        "high_income_volume": 6_600,
    },
    {
        "geo": "Tampa Bay",
        "pipeline_volume": 28_900,
        "quality_score": 78.4,
        "mover_cvr": 8.7,
        "benchmark": 6.1,
        "expansion_status": "Expanding",
        "high_income_cvr": 13.4,
        "high_income_volume": 6_100,
    },
    {
        "geo": "Denver",
        "pipeline_volume": 26_500,
        "quality_score": 74.1,
        "mover_cvr": 7.3,
        "benchmark": 6.1,
        "expansion_status": "New",
        "high_income_cvr": 11.5,
        "high_income_volume": 5_800,
    },
    {
        "geo": "Charlotte",
        "pipeline_volume": 24_300,
        "quality_score": 77.2,
        "mover_cvr": 8.4,
        "benchmark": 6.1,
        "expansion_status": "New",
        "high_income_cvr": 12.7,
        "high_income_volume": 5_100,
    },
    {
        "geo": "Nashville",
        "pipeline_volume": 22_700,
        "quality_score": 79.0,
        "mover_cvr": 9.1,
        "benchmark": 6.1,
        "expansion_status": "New",
        "high_income_cvr": 14.2,
        "high_income_volume": 4_700,
    },
    {
        "geo": "Austin",
        "pipeline_volume": 20_100,
        "quality_score": 80.3,
        "mover_cvr": 9.4,
        "benchmark": 6.1,
        "expansion_status": "New",
        "high_income_cvr": 14.8,
        "high_income_volume": 4_200,
    },
    {
        "geo": "Minneapolis",
        "pipeline_volume": 11_500,
        "quality_score": 68.4,
        "mover_cvr": 5.8,
        "benchmark": 6.1,
        "expansion_status": "Core",
        "high_income_cvr": 8.9,
        "high_income_volume": 2_400,
    },
]


# ---------------------------------------------------------------------------
# Public loaders
# ---------------------------------------------------------------------------

def load_life_events() -> list[dict]:
    """
    Return the 8 always-on life event campaigns with CVR metrics.

    Tries the ``life_event_campaigns`` table first; falls back to embedded
    mock data if the table is missing or empty.

    Returns
    -------
    list[dict] with keys:
        name, status, cvr, mass_market_cvr, cvr_multiplier,
        segment_size, key_params
    """
    try:
        conn = get_connection()
        df = conn.execute(
            """
            SELECT name, status, cvr, mass_market_cvr, cvr_multiplier,
                   segment_size, key_params
            FROM life_event_campaigns
            ORDER BY cvr_multiplier DESC
            """
        ).df()
        conn.close()
        if not df.empty:
            return df.to_dict("records")
    except Exception:
        pass

    return [dict(row) for row in _LIFE_EVENT_MOCK]


def load_movers() -> dict:
    """
    Return mover marketing data: top-line summary metrics and geo pipeline table.

    Tries the ``mover_pipeline`` table first; falls back to embedded mock data.

    Returns
    -------
    dict with keys:
        "summary": dict
            total_pipeline_volume: int
            avg_quality_score: float
            blended_mover_cvr: float
            propensity_benchmark: float  (x times mass-market CVR)
        "geo_table": pd.DataFrame
            Columns: geo, pipeline_volume, quality_score, mover_cvr,
                     benchmark, expansion_status, high_income_cvr,
                     high_income_volume
    """
    try:
        conn = get_connection()
        df = conn.execute(
            """
            SELECT geo, pipeline_volume, quality_score, mover_cvr,
                   benchmark, expansion_status, high_income_cvr,
                   high_income_volume
            FROM mover_pipeline
            ORDER BY pipeline_volume DESC
            """
        ).df()
        summary_row = conn.execute(
            """
            SELECT
                SUM(pipeline_volume)             AS total_pipeline_volume,
                AVG(quality_score)               AS avg_quality_score,
                SUM(pipeline_volume * mover_cvr) / NULLIF(SUM(pipeline_volume), 0)
                                                 AS blended_mover_cvr
            FROM mover_pipeline
            """
        ).fetchone()
        conn.close()
        if not df.empty:
            summary = {
                "total_pipeline_volume": int(summary_row[0] or 0),
                "avg_quality_score": round(float(summary_row[1] or 0), 1),
                "blended_mover_cvr": round(float(summary_row[2] or 0), 1),
                "propensity_benchmark": _MOVERS_SUMMARY["propensity_benchmark"],
            }
            return {"summary": summary, "geo_table": df}
    except Exception:
        pass

    return {
        "summary": dict(_MOVERS_SUMMARY),
        "geo_table": pd.DataFrame([dict(r) for r in _MOVERS_GEO_MOCK]),
    }
