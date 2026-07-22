"""Seed: Life Events Overlay Data (APE-19d / APE-100).

Generates two DataFrames:

  1. life_event_campaign_performance
     - 8 life event campaigns × 90 daily records
     - CVR multiplier 2–4x vs mass market baseline (Mass Market CVR = 0.112)
     - Total overlay spend reconciles to 12% of $15M total media budget = $1,800,000

  2. life_event_mover_pipeline
     - DMA-level weekly mover pipeline records, 12 weeks
     - 3–7x propensity CVR vs non-mover audience
     - Match rate 60–80% by data provider

Life event campaign definitions and CVR multipliers:
  New Mover              ~4.0x  (highest propensity)
  New Homeowner          ~3.5x
  New Parent             ~3.2x
  Marriage               ~3.0x
  Retirement             ~2.8x
  College                ~2.5x
  Job Change             ~2.3x
  Inheritance/Wealth Transfer  ~2.0x  (lowest)

Budget reconciliation:
  TOTAL_MEDIA_BUDGET = $15,000,000
  OVERLAY_BUDGET = 12% = $1,800,000
  Spend is distributed across 8 campaigns by weight; daily records sum to overlay total.

Idempotent: DROP + CREATE + INSERT for life_event_* tables.

Run:
    python -m src.data.seeds.life_events
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import date, timedelta
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema, Check
import duckdb

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
WORKSPACE = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if WORKSPACE not in sys.path:
    sys.path.insert(0, WORKSPACE)

from src.config.settings import DB_PATH  # noqa: E402
from src.data.seeds._dates import TRAILING_90D_START as START_DATE, TRAILING_90D_END as END_DATE

# ---------------------------------------------------------------------------
# RNG
# ---------------------------------------------------------------------------
SEED = 42
rng = np.random.default_rng(SEED)

# ---------------------------------------------------------------------------
# Date range — trailing 90 days ending yesterday
# ---------------------------------------------------------------------------
DATES: List[date] = [START_DATE + timedelta(days=i) for i in range(90)]

# ---------------------------------------------------------------------------
# Budget constants
# ---------------------------------------------------------------------------
TOTAL_MEDIA_BUDGET = 15_000_000.0
OVERLAY_BUDGET = TOTAL_MEDIA_BUDGET * 0.12   # $1,800,000

# Mass market baseline CVR (from seed_funnel.py PERSONA_BASELINE_CONV["Mass Market"])
MASS_MARKET_CVR = 0.112

# ---------------------------------------------------------------------------
# Life event campaign definitions
# ---------------------------------------------------------------------------
# (campaign_name, channel_slug, cvr_multiplier, budget_weight, start_offset_days)
# start_offset_days: campaigns ramp in at different times across the 90-day window
LIFE_EVENT_CAMPAIGNS: List[Tuple[str, str, float, float, int]] = [
    ("New Mover",                    "mover",       4.0, 0.22,  0),
    ("New Homeowner",                "life_event",  3.5, 0.18,  5),
    ("New Parent",                   "life_event",  3.2, 0.15,  7),
    ("Marriage",                     "life_event",  3.0, 0.13, 10),
    ("Retirement",                   "life_event",  2.8, 0.12, 14),
    ("College",                      "life_event",  2.5, 0.10, 21),
    ("Job Change",                   "life_event",  2.3, 0.06, 28),
    ("Inheritance/Wealth Transfer",  "life_event",  2.0, 0.04, 35),
]

CAMPAIGN_NAMES: List[str] = [c[0] for c in LIFE_EVENT_CAMPAIGNS]
CAMPAIGN_CHANNELS: List[str] = list({c[1] for c in LIFE_EVENT_CAMPAIGNS})

# Normalize budget weights to sum to 1.0
_raw_weights = np.array([c[3] for c in LIFE_EVENT_CAMPAIGNS], dtype=float)
CAMPAIGN_BUDGET_WEIGHTS: np.ndarray = _raw_weights / _raw_weights.sum()

# ---------------------------------------------------------------------------
# DMA data for mover pipeline (top 20 DMAs from seed_markets context)
# ---------------------------------------------------------------------------
DMA_LIST: List[Tuple[str, str]] = [
    # Codes and names aligned with seed_markets.py (APE-103 cross-channel consistency)
    ("501", "New York"),
    ("803", "Los Angeles"),
    ("602", "Chicago"),
    ("504", "Philadelphia"),
    ("539", "Tampa-St. Pete"),
    ("510", "Cleveland-Akron"),
    ("524", "Atlanta"),
    ("618", "Houston"),
    ("623", "Dallas-Fort Worth"),
    ("528", "Miami-Fort Lauderdale"),
    ("505", "Detroit"),
    ("506", "Boston"),
    ("807", "San Francisco-Oakland"),
    ("535", "Columbus"),
    ("659", "Nashville"),
    ("517", "Charlotte"),
    ("613", "Minneapolis-Saint Paul"),
    ("753", "Phoenix"),
    ("819", "Seattle-Tacoma"),
    ("751", "Denver"),
]

DATA_PROVIDERS: List[str] = ["CoreLogic", "Experian", "LexisNexis", "Acxiom", "TransUnion"]

# ---------------------------------------------------------------------------
# Seasonality helpers
# ---------------------------------------------------------------------------

def _dow_factor(d: date) -> float:
    dow = d.weekday()
    return 1.0 + 0.03 * (4 - abs(dow - 2)) if dow < 5 else 0.72


def _monthly_factor(d: date) -> float:
    return {
        1: 1.20, 2: 1.10, 3: 1.18, 4: 1.12, 5: 1.05,
        6: 0.95, 7: 0.88, 8: 0.92, 9: 1.05, 10: 1.15,
        11: 1.10, 12: 0.90,
    }[d.month]


def _season(d: date) -> float:
    return _dow_factor(d) * _monthly_factor(d)


# ---------------------------------------------------------------------------
# 1. life_event_campaign_performance — 8 campaigns × 90 days
# ---------------------------------------------------------------------------

def _build_campaign_performance() -> pd.DataFrame:
    """Generate daily campaign performance rows for 8 life event campaigns."""
    rows: List[dict] = []

    # Compute per-campaign total budget
    campaign_budgets = CAMPAIGN_BUDGET_WEIGHTS * OVERLAY_BUDGET  # shape (8,)

    for idx, (name, channel, cvr_mult, _weight, start_offset) in enumerate(LIFE_EVENT_CAMPAIGNS):
        campaign_id = str(uuid.uuid4())
        campaign_total_budget = campaign_budgets[idx]
        campaign_cvr = float(np.clip(MASS_MARKET_CVR * cvr_mult, 0.01, 0.95))

        # Only include dates after campaign start offset
        active_dates = [d for d in DATES if (d - START_DATE).days >= start_offset]
        n_active = len(active_dates)
        if n_active == 0:
            continue

        # Allocate budget across active days using a ramp-up pattern:
        # days start low and ramp to steady state over first 14 days
        ramp_days = min(14, n_active)
        ramp_weights = np.concatenate([
            np.linspace(0.4, 1.0, ramp_days),
            np.ones(n_active - ramp_days),
        ])
        # Add jitter
        jitter = rng.uniform(0.85, 1.15, size=n_active)
        raw_weights = ramp_weights * jitter
        day_spend_fractions = raw_weights / raw_weights.sum()
        daily_spends = day_spend_fractions * campaign_total_budget

        for day_idx, d in enumerate(active_dates):
            season = _season(d)
            spend = float(daily_spends[day_idx])

            # Impressions: life event campaigns run targeted, lower volume
            impressions = int(rng.integers(8_000, 25_000) * season)
            # CTR: 0.8–2.5% (targeted = higher engagement)
            ctr = float(np.clip(rng.uniform(0.008, 0.025) * season, 0.003, 0.08))
            clicks = int(impressions * ctr)

            # CVR with jitter
            cvr = float(np.clip(
                campaign_cvr + rng.uniform(-0.005, 0.005),
                0.01, 0.95,
            ))
            conversions = int(clicks * cvr)

            # CPA derived from spend / max(conversions, 1)
            cpa = spend / max(conversions, 1)

            rows.append({
                "id":            str(uuid.uuid4()),
                "campaign_id":   campaign_id,
                "campaign_name": name,
                "channel":       channel,
                "event_date":    d.isoformat(),
                "impressions":   impressions,
                "clicks":        clicks,
                "conversions":   conversions,
                "spend":         round(spend, 2),
                "ctr":           round(ctr, 4),
                "cvr":           round(cvr, 4),
                "cpa":           round(cpa, 2),
                "cvr_vs_baseline": round(cvr / MASS_MARKET_CVR, 4),
            })

    df = pd.DataFrame(rows)
    return df


# ---------------------------------------------------------------------------
# 2. life_event_mover_pipeline — DMA × provider × 12 weekly records
# ---------------------------------------------------------------------------

def _build_mover_pipeline() -> pd.DataFrame:
    """Generate mover pipeline rows: DMA × data provider × 12 weeks."""
    rows: List[dict] = []

    # 12 weekly periods ending on the last Sunday before END_DATE
    # Week 1 = START_DATE week, Week 12 = ~12 weeks later
    week_starts: List[date] = [START_DATE + timedelta(weeks=w) for w in range(12)]

    # Mover propensity CVR: 3–7x non-mover (we use MASS_MARKET_CVR as non-mover proxy)
    MOVER_PROPENSITY_RANGE = (3.0, 7.0)

    for week_num, week_start in enumerate(week_starts, start=1):
        for dma_code, dma_name in DMA_LIST:
            for provider in DATA_PROVIDERS:
                # Pipeline volume: movers identified in this DMA this week
                # Larger DMAs get higher volumes; add tier-based range
                dma_idx = next(i for i, (c, _) in enumerate(DMA_LIST) if c == dma_code)
                tier_factor = 1.0 if dma_idx < 7 else (0.65 if dma_idx < 14 else 0.40)
                pipeline_volume = int(
                    rng.integers(800, 3_500) * tier_factor
                    * (1.0 + 0.05 * rng.standard_normal())
                )
                pipeline_volume = max(pipeline_volume, 50)

                # Match rate: 60–80%
                match_rate = float(np.clip(rng.uniform(0.60, 0.80), 0.50, 0.90))
                matched_records = int(pipeline_volume * match_rate)

                # Propensity CVR multiplier within 3–7x
                propensity_mult = float(np.clip(
                    rng.uniform(*MOVER_PROPENSITY_RANGE),
                    MOVER_PROPENSITY_RANGE[0],
                    MOVER_PROPENSITY_RANGE[1],
                ))
                mover_cvr = float(np.clip(MASS_MARKET_CVR * propensity_mult, 0.01, 0.90))

                # Estimated conversions from matched mover pool
                conversions_est = int(matched_records * mover_cvr * 0.1)  # 10% contacted

                rows.append({
                    "id":                  str(uuid.uuid4()),
                    "week_num":            week_num,
                    "week_start":          week_start.isoformat(),
                    "dma_code":            dma_code,
                    "dma_name":            dma_name,
                    "data_provider":       provider,
                    "pipeline_volume":     pipeline_volume,
                    "match_rate":          round(match_rate, 4),
                    "matched_records":     matched_records,
                    "propensity_cvr_mult": round(propensity_mult, 4),
                    "mover_cvr":           round(mover_cvr, 4),
                    "conversions_est":     conversions_est,
                })

    df = pd.DataFrame(rows)
    return df


# ---------------------------------------------------------------------------
# Pandera schemas
# ---------------------------------------------------------------------------

CAMPAIGN_PERFORMANCE_SCHEMA = DataFrameSchema(
    {
        "id":               Column(str, nullable=False),
        "campaign_id":      Column(str, nullable=False),
        "campaign_name":    Column(str, Check.isin(CAMPAIGN_NAMES), nullable=False),
        "channel":          Column(str, nullable=False),
        "event_date":       Column(str, nullable=False),
        "impressions":      Column(int, Check.greater_than_or_equal_to(0), nullable=False),
        "clicks":           Column(int, Check.greater_than_or_equal_to(0), nullable=False),
        "conversions":      Column(int, Check.greater_than_or_equal_to(0), nullable=False),
        "spend":            Column(float, Check.greater_than_or_equal_to(0), nullable=False),
        "ctr":              Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "cvr":              Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "cpa":              Column(float, Check.greater_than_or_equal_to(0), nullable=False),
        "cvr_vs_baseline":  Column(float, Check.in_range(1.0, 10.0), nullable=False),
    },
    checks=[
        Check(lambda df: df["campaign_name"].nunique() == 8,
              error="life_event_campaign_performance: must have 8 distinct campaigns"),
        Check(
            lambda df: df.groupby("campaign_name")["cvr_vs_baseline"].mean().between(1.9, 4.1).all(),
            error="life_event_campaign_performance: mean cvr_vs_baseline must be ~2-4x per campaign",
        ),
        Check(
            lambda df: abs(df["spend"].sum() - OVERLAY_BUDGET) < 1.0,
            error=f"life_event_campaign_performance: total spend must equal ${OVERLAY_BUDGET:,.0f} ±$1",
        ),
        Check(
            lambda df: (df["clicks"] <= df["impressions"]).all(),
            error="life_event_campaign_performance: clicks must not exceed impressions",
        ),
        Check(
            lambda df: (df["conversions"] <= df["clicks"]).all(),
            error="life_event_campaign_performance: conversions must not exceed clicks",
        ),
    ],
    coerce=True,
)

MOVER_PIPELINE_SCHEMA = DataFrameSchema(
    {
        "id":                  Column(str, nullable=False),
        "week_num":            Column(int, Check.in_range(1, 12), nullable=False),
        "week_start":          Column(str, nullable=False),
        "dma_code":            Column(str, nullable=False),
        "dma_name":            Column(str, nullable=False),
        "data_provider":       Column(str, Check.isin(DATA_PROVIDERS), nullable=False),
        "pipeline_volume":     Column(int, Check.greater_than(0), nullable=False),
        "match_rate":          Column(float, Check.in_range(0.50, 0.90), nullable=False),
        "matched_records":     Column(int, Check.greater_than_or_equal_to(0), nullable=False),
        "propensity_cvr_mult": Column(float, Check.in_range(3.0, 7.0), nullable=False),
        "mover_cvr":           Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "conversions_est":     Column(int, Check.greater_than_or_equal_to(0), nullable=False),
    },
    checks=[
        Check(
            lambda df: len(df) == 12 * len(DMA_LIST) * len(DATA_PROVIDERS),
            error=f"life_event_mover_pipeline: expected {12 * len(DMA_LIST) * len(DATA_PROVIDERS)} rows",
        ),
        Check(
            lambda df: (df["matched_records"] <= df["pipeline_volume"]).all(),
            error="life_event_mover_pipeline: matched_records must not exceed pipeline_volume",
        ),
    ],
    coerce=True,
)


# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_DDL = [
    """
    CREATE TABLE IF NOT EXISTS life_event_campaign_performance (
        id                VARCHAR PRIMARY KEY,
        campaign_id       VARCHAR NOT NULL,
        campaign_name     VARCHAR NOT NULL,
        channel           VARCHAR NOT NULL,
        event_date        DATE NOT NULL,
        impressions       INTEGER DEFAULT 0,
        clicks            INTEGER DEFAULT 0,
        conversions       INTEGER DEFAULT 0,
        spend             DOUBLE DEFAULT 0,
        ctr               DOUBLE,
        cvr               DOUBLE,
        cpa               DOUBLE,
        cvr_vs_baseline   DOUBLE,
        created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS life_event_mover_pipeline (
        id                  VARCHAR PRIMARY KEY,
        week_num            INTEGER NOT NULL,
        week_start          DATE NOT NULL,
        dma_code            VARCHAR NOT NULL,
        dma_name            VARCHAR NOT NULL,
        data_provider       VARCHAR NOT NULL,
        pipeline_volume     INTEGER DEFAULT 0,
        match_rate          DOUBLE,
        matched_records     INTEGER DEFAULT 0,
        propensity_cvr_mult DOUBLE,
        mover_cvr           DOUBLE,
        conversions_est     INTEGER DEFAULT 0,
        created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
]


# ---------------------------------------------------------------------------
# DB helper
# ---------------------------------------------------------------------------

def _insert_df(conn: duckdb.DuckDBPyConnection, df: pd.DataFrame, table: str) -> None:
    conn.register("_tmp_le", df)
    cols = ", ".join(df.columns)
    conn.execute(f"INSERT INTO {table} ({cols}) SELECT {cols} FROM _tmp_le")
    conn.unregister("_tmp_le")


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------

def generate_life_events_data() -> Dict[str, pd.DataFrame]:
    """Generate life events overlay seed data.

    Returns:
        dict with keys:
            "campaign_performance" — daily campaign KPI rows (8 campaigns × ~90 days each)
            "mover_pipeline"       — DMA × provider × 12 weekly mover records
    """
    cp_df = _build_campaign_performance()
    mp_df = _build_mover_pipeline()

    # Validate
    CAMPAIGN_PERFORMANCE_SCHEMA.validate(cp_df)
    MOVER_PIPELINE_SCHEMA.validate(mp_df)

    return {
        "campaign_performance": cp_df,
        "mover_pipeline": mp_df,
    }


def seed(verbose: bool = True) -> Dict[str, pd.DataFrame]:
    """Seed life events tables into DuckDB. Returns dict of DataFrames."""
    from src.data.init_db import init_db
    init_db()

    conn = duckdb.connect(DB_PATH)

    # Recreate tables
    for tbl in ["life_event_campaign_performance", "life_event_mover_pipeline"]:
        conn.execute(f"DROP TABLE IF EXISTS {tbl}")
    for ddl in _DDL:
        conn.execute(ddl)

    if verbose:
        print("\n--- Building life_event_campaign_performance ---")
    cp_df = _build_campaign_performance()

    if verbose:
        total_spend = cp_df["spend"].sum()
        print(f"  Rows: {len(cp_df):,}")
        print(f"  Campaigns: {cp_df['campaign_name'].nunique()}")
        print(f"  Total spend: ${total_spend:,.2f}  (target: ${OVERLAY_BUDGET:,.2f})")
        print(f"  CVR vs baseline by campaign:")
        print(
            cp_df.groupby("campaign_name")["cvr_vs_baseline"]
            .mean()
            .sort_values(ascending=False)
            .apply(lambda x: f"  {x:.2f}x")
            .to_string()
        )

    if verbose:
        print("\n  Running Pandera validation on campaign_performance...")
    CAMPAIGN_PERFORMANCE_SCHEMA.validate(cp_df)
    if verbose:
        print("  Schema validation passed.")

    if verbose:
        print("\n--- Building life_event_mover_pipeline ---")
    mp_df = _build_mover_pipeline()

    if verbose:
        print(f"  Rows: {len(mp_df):,}")
        print(f"  DMAs: {mp_df['dma_code'].nunique()}")
        print(f"  Providers: {mp_df['data_provider'].nunique()}")
        avg_match = mp_df["match_rate"].mean()
        avg_mult = mp_df["propensity_cvr_mult"].mean()
        print(f"  Avg match rate: {avg_match:.1%}")
        print(f"  Avg propensity CVR mult: {avg_mult:.2f}x")

    if verbose:
        print("\n  Running Pandera validation on mover_pipeline...")
    MOVER_PIPELINE_SCHEMA.validate(mp_df)
    if verbose:
        print("  Schema validation passed.")

    # Write to DB
    if verbose:
        print("\n--- Writing to DB ---")

    _insert_df(conn, cp_df, "life_event_campaign_performance")
    db_cp = conn.execute("SELECT COUNT(*) FROM life_event_campaign_performance").fetchone()[0]
    if verbose:
        print(f"  life_event_campaign_performance: {db_cp:,} rows written.")

    _insert_df(conn, mp_df, "life_event_mover_pipeline")
    db_mp = conn.execute("SELECT COUNT(*) FROM life_event_mover_pipeline").fetchone()[0]
    if verbose:
        print(f"  life_event_mover_pipeline: {db_mp:,} rows written.")

    conn.commit()
    conn.close()

    if verbose:
        print("\nLife events tables seeded successfully.")

    return {"campaign_performance": cp_df, "mover_pipeline": mp_df}


if __name__ == "__main__":
    import time
    t0 = time.perf_counter()
    result = seed(verbose=True)
    elapsed = time.perf_counter() - t0
    cp = result["campaign_performance"]
    mp = result["mover_pipeline"]
    print(f"\nDone in {elapsed:.2f}s")
    print(f"  campaign_performance rows: {len(cp):,}")
    print(f"  mover_pipeline rows:       {len(mp):,}")
    print(f"  Total overlay spend: ${cp['spend'].sum():,.2f}")
    print(f"  Spend reconciliation check: {'PASS' if abs(cp['spend'].sum() - 1_800_000.0) < 1.0 else 'FAIL'}")
