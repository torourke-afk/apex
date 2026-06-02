"""Seed: DMA Market Data

Generates 20 rows — one per Designated Market Area (DMA) — covering Tier 1,
Tier 2, and Tier 3 markets with brand health, retention, and customer metrics.

Targets the `markets` table (APE-62 schema):
    id, dma_code, dma_name, tier, state, population, hhi_median,
    branch_count, digital_adoption_pct, brand_awareness_pct,
    brand_consideration_pct, brand_health_score, retention_6m,
    retention_12m, nps_score, active_customers, avg_ltv,
    created_at, updated_at

Market tiers (based on DMA population + strategic priority):
  Tier 1 (10 markets): Top-10 US DMAs — highest population, full branch presence
  Tier 2  (7 markets): Mid-size strategic expansion markets
  Tier 3  (3 markets): Emerging / growth opportunity markets

Brand health metrics follow realistic bank benchmarks:
  - Awareness decreases by tier (Tier 1: 55–70%, Tier 2: 35–55%, Tier 3: 20–38%)
  - Consideration tracks awareness with a 40–55% conversion ratio
  - Brand health score: composite 0–100 scale
  - Retention is higher in Tier 1 (deeper relationships)
  - NPS benchmarks: Tier 1 ~32, Tier 2 ~28, Tier 3 ~22

Idempotent: DELETE + INSERT.

Run:
    python -m src.data.seeds.seed_markets
"""

from __future__ import annotations

import os
import sys
import uuid
from typing import List

import numpy as np
import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema, Check

WORKSPACE = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if WORKSPACE not in sys.path:
    sys.path.insert(0, WORKSPACE)

from src.data.init_db import get_connection  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEED = 77
rng = np.random.default_rng(SEED)

VALID_TIERS = [1, 2, 3]

# DMA definitions: (dma_code, dma_name, tier, state, population_base, hhi_median_base,
#                   branch_count_base, digital_adoption_base,
#                   awareness_base, consideration_ratio, retention_6m_base,
#                   retention_12m_base, nps_base, customer_base, ltv_base)
# Branch counts, customers, and LTV are adjusted by tier.
DMA_DATA = [
    # --- Tier 1 (top-10 DMAs) ---
    ("501",  "New York",                1, "NY",  20_000_000, 75_000, 145, 0.72, 0.67, 0.50, 0.88, 0.79, 34.0, 310_000, 4_850),
    ("803",  "Los Angeles",             1, "CA",  16_000_000, 68_000, 112, 0.74, 0.62, 0.48, 0.86, 0.77, 31.0, 240_000, 4_620),
    ("602",  "Chicago",                 1, "IL",   9_500_000, 66_000,  88, 0.70, 0.64, 0.49, 0.87, 0.78, 33.0, 175_000, 4_700),
    ("504",  "Philadelphia",            1, "PA",   7_200_000, 63_000,  72, 0.68, 0.60, 0.47, 0.86, 0.77, 30.0, 130_000, 4_500),
    ("623",  "Dallas-Fort Worth",       1, "TX",   7_800_000, 67_000,  78, 0.73, 0.61, 0.49, 0.87, 0.78, 32.0, 148_000, 4_580),
    ("807",  "San Francisco-Oakland",   1, "CA",   7_000_000, 95_000,  65, 0.80, 0.58, 0.47, 0.85, 0.76, 35.0, 118_000, 5_200),
    ("524",  "Atlanta",                 1, "GA",   6_500_000, 64_000,  68, 0.71, 0.59, 0.46, 0.86, 0.76, 31.0, 120_000, 4_550),
    ("506",  "Boston",                  1, "MA",   5_400_000, 82_000,  58, 0.76, 0.63, 0.49, 0.88, 0.79, 36.0, 102_000, 5_100),
    ("528",  "Miami-Fort Lauderdale",   1, "FL",   6_200_000, 62_000,  70, 0.69, 0.57, 0.45, 0.85, 0.75, 28.0, 108_000, 4_400),
    ("618",  "Houston",                 1, "TX",   6_800_000, 61_000,  74, 0.70, 0.60, 0.47, 0.86, 0.77, 30.0, 128_000, 4_480),
    # --- Tier 2 (strategic expansion) ---
    ("753",  "Phoenix",                 2, "AZ",   4_900_000, 58_000,  42, 0.67, 0.48, 0.44, 0.83, 0.73, 27.0,  68_000, 4_100),
    ("505",  "Detroit",                 2, "MI",   4_300_000, 57_000,  40, 0.63, 0.50, 0.44, 0.83, 0.73, 28.0,  62_000, 4_050),
    ("613",  "Minneapolis-Saint Paul",  2, "MN",   3_700_000, 72_000,  38, 0.70, 0.52, 0.45, 0.84, 0.74, 30.0,  57_000, 4_300),
    ("819",  "Seattle-Tacoma",          2, "WA",   4_100_000, 85_000,  36, 0.77, 0.49, 0.44, 0.83, 0.73, 32.0,  60_000, 4_700),
    ("539",  "Tampa-St. Pete",          2, "FL",   3_200_000, 57_000,  35, 0.65, 0.46, 0.43, 0.82, 0.72, 26.0,  48_000, 3_950),
    ("751",  "Denver",                  2, "CO",   3_500_000, 74_000,  34, 0.72, 0.50, 0.44, 0.83, 0.73, 30.0,  52_000, 4_400),
    ("510",  "Cleveland-Akron",         2, "OH",   2_900_000, 54_000,  32, 0.60, 0.47, 0.43, 0.82, 0.72, 25.0,  42_000, 3_900),
    # --- Tier 3 (emerging / growth) ---
    ("517",  "Charlotte",               3, "NC",   2_700_000, 60_000,  24, 0.64, 0.32, 0.40, 0.79, 0.68, 23.0,  28_000, 3_700),
    ("659",  "Nashville",               3, "TN",   2_400_000, 61_000,  22, 0.63, 0.30, 0.39, 0.79, 0.68, 22.0,  24_000, 3_650),
    ("535",  "Columbus",                3, "OH",   2_200_000, 58_000,  20, 0.62, 0.28, 0.39, 0.78, 0.67, 21.0,  20_000, 3_600),
]


# ---------------------------------------------------------------------------
# Row builder
# ---------------------------------------------------------------------------

def build_rows() -> List[dict]:
    """Build 20 market rows (one per DMA)."""
    rows: List[dict] = []
    now = pd.Timestamp.now()

    for (dma_code, dma_name, tier, state, pop_base, hhi_base, branch_base,
         digital_base, awareness_base, consid_ratio, ret6_base, ret12_base,
         nps_base, cust_base, ltv_base) in DMA_DATA:

        # Add small noise to simulate realistic variance between markets
        pop = int(pop_base * float(rng.uniform(0.95, 1.05)))
        hhi = int(hhi_base * float(rng.uniform(0.97, 1.03)))
        branches = max(1, int(branch_base + rng.integers(-3, 4)))
        digital = float(np.clip(digital_base + rng.uniform(-0.03, 0.03), 0.40, 0.95))
        awareness = float(np.clip(awareness_base + rng.uniform(-0.02, 0.02), 0.10, 0.85))
        consideration = float(np.clip(awareness * consid_ratio + rng.uniform(-0.02, 0.02), 0.05, 0.50))

        # Brand health score: composite of awareness, consideration, and retention
        brand_health = float(np.clip(
            (awareness * 0.40 + consideration * 0.25 + ret12_base * 0.35) * 100,
            0.0, 100.0
        ))

        ret_6m = float(np.clip(ret6_base + rng.uniform(-0.02, 0.02), 0.60, 0.97))
        ret_12m = float(np.clip(ret12_base + rng.uniform(-0.03, 0.03), 0.50, 0.95))
        # Enforce ret_12m <= ret_6m (12-month cohort is always smaller)
        ret_12m = min(ret_12m, ret_6m)

        nps = float(np.clip(nps_base + rng.uniform(-2.0, 2.0), -10.0, 70.0))
        customers = max(1000, int(cust_base * float(rng.uniform(0.93, 1.07))))
        ltv = float(ltv_base * float(rng.uniform(0.95, 1.05)))

        rows.append({
            "id":                      str(uuid.uuid4()),
            "dma_code":                dma_code,
            "dma_name":                dma_name,
            "tier":                    tier,
            "state":                   state,
            "population":              pop,
            "hhi_median":              hhi,
            "branch_count":            branches,
            "digital_adoption_pct":    round(digital, 4),
            "brand_awareness_pct":     round(awareness, 4),
            "brand_consideration_pct": round(consideration, 4),
            "brand_health_score":      round(brand_health, 4),
            "retention_6m":            round(ret_6m, 4),
            "retention_12m":           round(ret_12m, 4),
            "nps_score":               round(nps, 2),
            "active_customers":        customers,
            "avg_ltv":                 round(ltv, 2),
            "created_at":              now,
            "updated_at":              now,
        })

    return rows


# ---------------------------------------------------------------------------
# Pandera schema
# ---------------------------------------------------------------------------

MARKETS_SCHEMA = DataFrameSchema(
    {
        "id":                      Column(str, nullable=False),
        "dma_code":                Column(str, nullable=False),
        "dma_name":                Column(str, nullable=False),
        "tier":                    Column(int, Check.isin(VALID_TIERS), nullable=False),
        "state":                   Column(str, nullable=False),
        "population":              Column(int, Check.greater_than(0), nullable=False),
        "hhi_median":              Column(int, Check.greater_than(0), nullable=False),
        "branch_count":            Column(int, Check.greater_than_or_equal_to(1), nullable=False),
        "digital_adoption_pct":    Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "brand_awareness_pct":     Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "brand_consideration_pct": Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "brand_health_score":      Column(float, Check.in_range(0.0, 100.0), nullable=False),
        "retention_6m":            Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "retention_12m":           Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "nps_score":               Column(float, Check.in_range(-100.0, 100.0), nullable=False),
        "active_customers":        Column(int, Check.greater_than(0), nullable=False),
        "avg_ltv":                 Column(float, Check.greater_than(0), nullable=False),
    },
    checks=[
        Check(lambda df: len(df) == 20, error="markets: expected exactly 20 DMA rows"),
        Check(lambda df: df["dma_code"].nunique() == 20, error="markets: dma_code must be unique"),
        Check(lambda df: (df["tier"] == 1).sum() == 10, error="markets: expected 10 Tier 1 markets"),
        Check(lambda df: (df["tier"] == 2).sum() == 7, error="markets: expected 7 Tier 2 markets"),
        Check(lambda df: (df["tier"] == 3).sum() == 3, error="markets: expected 3 Tier 3 markets"),
        Check(
            lambda df: (df["retention_12m"] <= df["retention_6m"]).all(),
            error="markets: retention_12m must be <= retention_6m",
        ),
        Check(
            lambda df: (df["brand_consideration_pct"] <= df["brand_awareness_pct"]).all(),
            error="markets: consideration must be <= awareness",
        ),
        Check(
            lambda df: df.groupby("tier")["brand_awareness_pct"].mean().is_monotonic_decreasing,
            error="markets: mean brand awareness must decrease from Tier 1 → Tier 3",
        ),
    ],
    coerce=True,
)


# ---------------------------------------------------------------------------
# Seed function
# ---------------------------------------------------------------------------

def seed(verbose: bool = True) -> pd.DataFrame:
    """Build and insert DMA market seed data into DuckDB. Idempotent."""
    rows = build_rows()
    df = pd.DataFrame(rows)

    for col in ["digital_adoption_pct", "brand_awareness_pct", "brand_consideration_pct",
                "brand_health_score", "retention_6m", "retention_12m",
                "nps_score", "avg_ltv"]:
        df[col] = df[col].astype(float)
    for col in ["population", "hhi_median", "branch_count", "active_customers", "tier"]:
        df[col] = df[col].astype(int)

    MARKETS_SCHEMA.validate(df)

    conn = get_connection()
    try:
        conn.execute("DELETE FROM markets")
        conn.register("mkts_df", df)
        conn.execute("""
            INSERT INTO markets
                (id, dma_code, dma_name, tier, state, population, hhi_median,
                 branch_count, digital_adoption_pct, brand_awareness_pct,
                 brand_consideration_pct, brand_health_score, retention_6m,
                 retention_12m, nps_score, active_customers, avg_ltv,
                 created_at, updated_at)
            SELECT id, dma_code, dma_name, tier, state, population, hhi_median,
                   branch_count, digital_adoption_pct, brand_awareness_pct,
                   brand_consideration_pct, brand_health_score, retention_6m,
                   retention_12m, nps_score, active_customers, avg_ltv,
                   created_at, updated_at
            FROM mkts_df
        """)
        conn.commit()
    finally:
        conn.unregister("mkts_df")
        conn.close()

    if verbose:
        print(f"[seed_markets] Inserted {len(df)} rows into markets")
        print(f"  Tier 1: {(df['tier'] == 1).sum()} DMAs")
        print(f"  Tier 2: {(df['tier'] == 2).sum()} DMAs")
        print(f"  Tier 3: {(df['tier'] == 3).sum()} DMAs")
        print(f"  Total active customers: {df['active_customers'].sum():,}")
        by_tier = df.groupby("tier").agg(
            awareness=("brand_awareness_pct", "mean"),
            health=("brand_health_score", "mean"),
            ret_12m=("retention_12m", "mean"),
            nps=("nps_score", "mean"),
            customers=("active_customers", "sum"),
        )
        print("\n  Tier averages:")
        for tier, row in by_tier.iterrows():
            print(f"    Tier {tier}: awareness={row['awareness']:.1%}  "
                  f"health={row['health']:.1f}  "
                  f"ret_12m={row['ret_12m']:.1%}  "
                  f"NPS={row['nps']:.1f}  "
                  f"customers={row['customers']:,}")
        print()

    return df


if __name__ == "__main__":
    seed()
