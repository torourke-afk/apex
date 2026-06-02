"""Seed: Budget Allocation Data

Generates 72 rows (6 categories × 12 months) of budget pacing data for the
spend dashboard.

Targets the production `budgets` table (APE-9 schema):
    id, name, channel, period, period_start, allocated, actual,
    created_at, updated_at

Budget categories and annual totals ($15M total):
    Brand Media:          $6,000,000  (40%)
    Performance SEM:      $3,750,000  (25%)
    Paid Social:          $2,250,000  (15%)
    High-Value Overlay:   $1,800,000  (12%)
    SEO/AEO:                $750,000   (5%)
    Conversion/Testing:     $450,000   (3%)

Monthly pacing: seasonal weights applied per category; `actual` deviates 5–8%
from `allocated` with realistic directional noise (over/under-spend).

Idempotent: DELETE + INSERT.

Run:
    python -m src.data.seeds.budgets
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import date
from typing import List

import numpy as np
import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema, Check

# ---------------------------------------------------------------------------
# Path bootstrap (allows running as script or module)
# ---------------------------------------------------------------------------
WORKSPACE = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if WORKSPACE not in sys.path:
    sys.path.insert(0, WORKSPACE)

from src.data.init_db import get_connection  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEED = 42
rng = np.random.default_rng(SEED)

ANNUAL_TOTAL = 15_000_000.0

# 6 budget categories: (name, channel_slug, annual_amount)
CATEGORIES = [
    ("Brand Media",          "brand_media",          6_000_000.0),
    ("Performance SEM",      "paid_search",           3_750_000.0),
    ("Paid Social",          "paid_social",           2_250_000.0),
    ("High-Value Overlay",   "high_value_overlay",    1_800_000.0),
    ("SEO/AEO",              "seo_aeo",                 750_000.0),
    ("Conversion/Testing",   "conversion_testing",      450_000.0),
]

# Trailing 12 months: May 2025 – April 2026 (period_start = 1st of each month)
MONTHS: List[date] = [
    date(2025, 5, 1),
    date(2025, 6, 1),
    date(2025, 7, 1),
    date(2025, 8, 1),
    date(2025, 9, 1),
    date(2025, 10, 1),
    date(2025, 11, 1),
    date(2025, 12, 1),
    date(2026, 1, 1),
    date(2026, 2, 1),
    date(2026, 3, 1),
    date(2026, 4, 1),
]

# Seasonal pacing weights per month index (0=May … 11=April).
# Each category has a 12-element weight vector; they are normalised to sum to
# annual_amount when multiplied by that category's total.
#
# Design notes:
#   - Brand Media spikes in Q4 (holiday) and Jan (new-year brand push)
#   - Performance SEM peaks Q4 and Q1 acquisition pushes
#   - Paid Social: Q4 + summer
#   - High-Value Overlay: steady with slight Q4/Q1 lift
#   - SEO/AEO: relatively flat (content cadence)
#   - Conversion/Testing: heavier Q3–Q4 (test cycles before year-end)
PACING_WEIGHTS = {
    "brand_media":         [0.070, 0.075, 0.085, 0.085, 0.080, 0.095, 0.105, 0.110, 0.095, 0.075, 0.068, 0.057],
    "paid_search":         [0.075, 0.078, 0.080, 0.082, 0.080, 0.095, 0.100, 0.108, 0.095, 0.080, 0.070, 0.057],
    "paid_social":         [0.072, 0.080, 0.090, 0.092, 0.078, 0.090, 0.095, 0.105, 0.090, 0.075, 0.068, 0.065],
    "high_value_overlay":  [0.080, 0.082, 0.082, 0.084, 0.082, 0.088, 0.090, 0.095, 0.090, 0.082, 0.078, 0.067],
    "seo_aeo":             [0.082, 0.083, 0.083, 0.085, 0.083, 0.085, 0.085, 0.087, 0.084, 0.082, 0.080, 0.071],
    "conversion_testing":  [0.075, 0.078, 0.082, 0.085, 0.082, 0.090, 0.095, 0.100, 0.085, 0.080, 0.072, 0.076],
}

# Variance band: actual = allocated × (1 + ε), ε ~ Uniform(-0.08, +0.08)
# but clamped so |ε| ∈ [0.05, 0.08] to guarantee meaningful 5–8% deviation.
VARIANCE_MIN = 0.05
VARIANCE_MAX = 0.08

VALID_CHANNELS = [cat[1] for cat in CATEGORIES]


# ---------------------------------------------------------------------------
# Row builder
# ---------------------------------------------------------------------------

def build_rows() -> List[dict]:
    """Build 72 budget rows (6 categories × 12 months)."""
    rows: List[dict] = []
    now = pd.Timestamp.now()

    for cat_name, channel, annual_amount in CATEGORIES:
        weights = np.array(PACING_WEIGHTS[channel], dtype=float)
        # Normalise so weights sum to 1 → monthly_planned = annual × weight
        weights /= weights.sum()
        monthly_planned = weights * annual_amount

        for idx, period_start in enumerate(MONTHS):
            allocated = round(float(monthly_planned[idx]), 4)

            # Signed variance: draw magnitude then sign separately for
            # directional realism (not always over or under)
            magnitude = float(rng.uniform(VARIANCE_MIN, VARIANCE_MAX))
            sign = float(rng.choice([-1, 1]))
            actual = round(allocated * (1 + sign * magnitude), 4)

            rows.append({
                "id":           str(uuid.uuid4()),
                "name":         f"{cat_name} – {period_start.strftime('%b %Y')}",
                "channel":      channel,
                "period":       "monthly",
                "period_start": period_start,
                "allocated":    allocated,
                "actual":       actual,
                "created_at":   now,
                "updated_at":   now,
            })

    return rows


# ---------------------------------------------------------------------------
# Pandera schema
# ---------------------------------------------------------------------------

BUDGET_SCHEMA = DataFrameSchema(
    {
        "id":           Column(str, nullable=False),
        "name":         Column(str, nullable=False),
        "channel":      Column(str, Check.isin(VALID_CHANNELS)),
        "period":       Column(str, Check.isin(["monthly", "quarterly", "annual"])),
        "period_start": Column("object", nullable=False),
        "allocated":    Column(float, Check.greater_than(0)),
        "actual":       Column(float, Check.greater_than(0)),
    },
    checks=[
        Check(
            lambda df: len(df) >= 72,
            error="Expected >= 72 rows (6 categories × 12 months)",
        ),
        Check(
            lambda df: df["channel"].nunique() == 6,
            error="Expected 6 distinct budget channels",
        ),
        Check(
            lambda df: df.groupby("channel")["period_start"].nunique().eq(12).all(),
            error="Each channel must have exactly 12 monthly entries",
        ),
        Check(
            lambda df: (
                (df["actual"] / df["allocated"]).between(1 - VARIANCE_MAX - 0.001, 1 + VARIANCE_MAX + 0.001)
            ).all(),
            error="actual/allocated ratio must stay within ±8% band",
        ),
        Check(
            lambda df: abs(df["allocated"].sum() - ANNUAL_TOTAL) < 1.0,
            error=f"Sum of allocated must equal ${ANNUAL_TOTAL:,.0f} (±$1)",
        ),
    ],
    coerce=True,
)


# ---------------------------------------------------------------------------
# Seed function
# ---------------------------------------------------------------------------

def seed(verbose: bool = True) -> pd.DataFrame:
    """
    Build and insert budget seed data into DuckDB.

    Idempotent — DELETE + INSERT on the `budgets` table.
    Returns the seeded DataFrame.
    """
    rows = build_rows()
    df = pd.DataFrame(rows)

    # Coerce numeric columns to float for pandera
    df["allocated"] = df["allocated"].astype(float)
    df["actual"] = df["actual"].astype(float)

    # Validate
    BUDGET_SCHEMA.validate(df)

    conn = get_connection()
    try:
        conn.execute("DELETE FROM budgets")
        conn.register("budget_df", df)
        conn.execute("""
            INSERT INTO budgets
                (id, name, channel, period, period_start,
                 allocated, actual, created_at, updated_at)
            SELECT id, name, channel, period, period_start,
                   allocated, actual, created_at, updated_at
            FROM budget_df
        """)
        conn.commit()
    finally:
        conn.unregister("budget_df")
        conn.close()

    if verbose:
        annual_allocated = df["allocated"].sum()
        annual_actual = df["actual"].sum()
        print(f"[seed_budgets] Inserted {len(df)} rows into budgets")
        print(f"  Categories:       {df['channel'].nunique()}")
        print(f"  Months per cat:   {df.groupby('channel')['period_start'].nunique().iloc[0]}")
        print(f"  Annual allocated: ${annual_allocated:>14,.2f}")
        print(f"  Annual actual:    ${annual_actual:>14,.2f}")
        print(f"  Variance (actual/allocated):")
        ratio = df["actual"] / df["allocated"]
        print(f"    min={ratio.min():.4f}  max={ratio.max():.4f}  mean={ratio.mean():.4f}")
        print()
        by_cat = (
            df.groupby("channel")[["allocated", "actual"]]
            .sum()
            .sort_values("allocated", ascending=False)
        )
        print("  Category breakdown (annual):")
        for ch, row in by_cat.iterrows():
            pct = row["allocated"] / ANNUAL_TOTAL * 100
            print(f"    {ch:<25}  alloc=${row['allocated']:>12,.0f}  "
                  f"actual=${row['actual']:>12,.0f}  ({pct:.0f}%)")

    return df


if __name__ == "__main__":
    seed()
