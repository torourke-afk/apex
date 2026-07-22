"""Seed: Budget Pacing Actuals

Generates 288 rows (6 channels × 12 months × 4 weeks) of weekly budget pacing
actuals for the spend dashboard.

Targets the `budget_pacing` table (APE-62 schema):
    id, channel, period_month, week_num, week_start, weekly_planned,
    weekly_actual, cumulative_planned, cumulative_actual, pacing_rate,
    forecast_eom, variance_pct, pacing_status, created_at, updated_at

Design notes:
  - Each monthly budget is split into 4 equal weekly tranches (planned).
  - Weekly actuals deviate from plan ±3–12%; noise is correlated within a month
    so over/under spend persists (realistic front-loading or back-loading).
  - pacing_rate  = cumulative_actual / cumulative_planned (clipped to 4 decimal places)
  - forecast_eom = cumulative_actual + remaining_planned × channel_trend_factor
  - pacing_status: on_track (0.95–1.05), over (>1.05), under (<0.95)
  - Channel allocations match budgets.py CATEGORIES.

Idempotent: DELETE + INSERT.

Run:
    python -m src.data.seeds.seed_budget_pacing
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import date, timedelta
from typing import List

import numpy as np
import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema, Check

from src.data.seeds._dates import FY_MONTH_STARTS

WORKSPACE = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if WORKSPACE not in sys.path:
    sys.path.insert(0, WORKSPACE)

from src.data.init_db import get_connection  # noqa: E402

# ---------------------------------------------------------------------------
# Constants (mirror budgets.py)
# ---------------------------------------------------------------------------
SEED = 99
rng = np.random.default_rng(SEED)

ANNUAL_TOTAL = 15_000_000.0

CATEGORIES = [
    ("brand_media",         6_000_000.0),
    ("paid_search",         3_750_000.0),
    ("paid_social",         2_250_000.0),
    ("high_value_overlay",  1_800_000.0),
    ("seo_aeo",               750_000.0),
    ("conversion_testing",    450_000.0),
]

PACING_WEIGHTS = {
    "brand_media":         [0.070, 0.075, 0.085, 0.085, 0.080, 0.095, 0.105, 0.110, 0.095, 0.075, 0.068, 0.057],
    "paid_search":         [0.075, 0.078, 0.080, 0.082, 0.080, 0.095, 0.100, 0.108, 0.095, 0.080, 0.070, 0.057],
    "paid_social":         [0.072, 0.080, 0.090, 0.092, 0.078, 0.090, 0.095, 0.105, 0.090, 0.075, 0.068, 0.065],
    "high_value_overlay":  [0.080, 0.082, 0.082, 0.084, 0.082, 0.088, 0.090, 0.095, 0.090, 0.082, 0.078, 0.067],
    "seo_aeo":             [0.082, 0.083, 0.083, 0.085, 0.083, 0.085, 0.085, 0.087, 0.084, 0.082, 0.080, 0.071],
    "conversion_testing":  [0.075, 0.078, 0.082, 0.085, 0.082, 0.090, 0.095, 0.100, 0.085, 0.080, 0.072, 0.076],
}

# Fiscal-year month starts (12 months, computed from _dates anchor)
MONTHS: List[date] = [ts.date() for ts in FY_MONTH_STARTS]

VALID_CHANNELS = [c[0] for c in CATEGORIES]
VALID_STATUSES = ["on_track", "over", "under"]

# Weekly intra-month variance bands per channel (min_pct, max_pct).
# Brand Media and Paid Social tend to front-load; SEO is flat.
CHANNEL_VARIANCE = {
    "brand_media":        (0.04, 0.12),
    "paid_search":        (0.03, 0.10),
    "paid_social":        (0.05, 0.12),
    "high_value_overlay": (0.02, 0.08),
    "seo_aeo":            (0.01, 0.05),
    "conversion_testing": (0.03, 0.10),
}

# Front-load bias (>0 means tend to over-spend early; <0 means back-load)
CHANNEL_BIAS = {
    "brand_media":        0.03,   # slight front-load
    "paid_search":        0.00,   # neutral
    "paid_social":        0.04,   # front-load
    "high_value_overlay": -0.01,  # slight back-load
    "seo_aeo":            0.00,
    "conversion_testing": -0.02,  # back-load (test cycles)
}


# ---------------------------------------------------------------------------
# Row builder
# ---------------------------------------------------------------------------

def build_rows() -> List[dict]:
    """Build 288 budget pacing rows (6 channels × 12 months × 4 weeks)."""
    rows: List[dict] = []
    now = pd.Timestamp.now()

    for channel, annual_amount in CATEGORIES:
        weights = np.array(PACING_WEIGHTS[channel], dtype=float)
        weights /= weights.sum()
        monthly_planned = weights * annual_amount

        v_min, v_max = CHANNEL_VARIANCE[channel]
        bias = CHANNEL_BIAS[channel]

        for month_idx, period_month in enumerate(MONTHS):
            monthly_budget = monthly_planned[month_idx]
            # 4 equal weekly planned tranches
            weekly_plan_base = monthly_budget / 4.0

            # Draw 4 correlated noise values for this channel×month
            # Correlated via shared month-level drift
            month_drift = float(rng.uniform(-0.04, 0.04)) + bias
            week_noises = rng.uniform(-v_max, v_max, size=4) + month_drift

            cumulative_planned = 0.0
            cumulative_actual = 0.0

            for week_num in range(1, 5):
                week_start = period_month + timedelta(weeks=week_num - 1)
                weekly_planned_amt = weekly_plan_base
                noise = float(np.clip(week_noises[week_num - 1], -v_max, v_max))
                weekly_actual_amt = weekly_planned_amt * (1.0 + noise)
                weekly_actual_amt = max(weekly_actual_amt, 0.0)

                cumulative_planned += weekly_planned_amt
                cumulative_actual += weekly_actual_amt

                pacing_rate = cumulative_actual / cumulative_planned if cumulative_planned > 0 else 1.0

                # Forecast EOM: cumulative_actual + remaining planned scaled by trend
                weeks_remaining = 4 - week_num
                trend = pacing_rate  # assume current rate continues
                forecast_eom = cumulative_actual + (weeks_remaining * weekly_plan_base * trend)

                variance_pct = (cumulative_actual - cumulative_planned) / cumulative_planned if cumulative_planned > 0 else 0.0

                if pacing_rate > 1.05:
                    pacing_status = "over"
                elif pacing_rate < 0.95:
                    pacing_status = "under"
                else:
                    pacing_status = "on_track"

                rows.append({
                    "id":                 str(uuid.uuid4()),
                    "channel":            channel,
                    "period_month":       period_month,
                    "week_num":           week_num,
                    "week_start":         week_start,
                    "weekly_planned":     round(weekly_planned_amt, 4),
                    "weekly_actual":      round(weekly_actual_amt, 4),
                    "cumulative_planned": round(cumulative_planned, 4),
                    "cumulative_actual":  round(cumulative_actual, 4),
                    "pacing_rate":        round(pacing_rate, 6),
                    "forecast_eom":       round(forecast_eom, 4),
                    "variance_pct":       round(variance_pct, 6),
                    "pacing_status":      pacing_status,
                    "created_at":         now,
                    "updated_at":         now,
                })

    return rows


# ---------------------------------------------------------------------------
# Pandera schema
# ---------------------------------------------------------------------------

BUDGET_PACING_SCHEMA = DataFrameSchema(
    {
        "id":                 Column(str, nullable=False),
        "channel":            Column(str, Check.isin(VALID_CHANNELS), nullable=False),
        "period_month":       Column("object", nullable=False),
        "week_num":           Column(int, Check.isin([1, 2, 3, 4]), nullable=False),
        "week_start":         Column("object", nullable=False),
        "weekly_planned":     Column(float, Check.greater_than(0), nullable=False),
        "weekly_actual":      Column(float, Check.greater_than_or_equal_to(0), nullable=False),
        "cumulative_planned": Column(float, Check.greater_than(0), nullable=False),
        "cumulative_actual":  Column(float, Check.greater_than_or_equal_to(0), nullable=False),
        "pacing_rate":        Column(float, Check.in_range(0.5, 2.0), nullable=False),
        "forecast_eom":       Column(float, Check.greater_than_or_equal_to(0), nullable=False),
        "variance_pct":       Column(float, nullable=False),
        "pacing_status":      Column(str, Check.isin(VALID_STATUSES), nullable=False),
    },
    checks=[
        Check(
            lambda df: len(df) == 288,
            error="budget_pacing: expected exactly 288 rows (6 channels × 12 months × 4 weeks)",
        ),
        Check(
            lambda df: df["channel"].nunique() == 6,
            error="budget_pacing: expected 6 distinct channels",
        ),
        Check(
            lambda df: df.groupby(["channel", "period_month"])["week_num"].nunique().eq(4).all(),
            error="budget_pacing: each channel×month must have exactly 4 weekly entries",
        ),
        Check(
            lambda df: (df["pacing_rate"] > 0).all(),
            error="budget_pacing: pacing_rate must be positive",
        ),
    ],
    coerce=True,
)


# ---------------------------------------------------------------------------
# Seed function
# ---------------------------------------------------------------------------

def seed(verbose: bool = True) -> pd.DataFrame:
    """Build and insert budget pacing seed data into DuckDB. Idempotent."""
    rows = build_rows()
    df = pd.DataFrame(rows)

    for col in ["weekly_planned", "weekly_actual", "cumulative_planned",
                "cumulative_actual", "pacing_rate", "forecast_eom", "variance_pct"]:
        df[col] = df[col].astype(float)
    df["week_num"] = df["week_num"].astype(int)

    BUDGET_PACING_SCHEMA.validate(df)

    conn = get_connection()
    try:
        conn.execute("DELETE FROM budget_pacing")
        conn.register("bp_df", df)
        conn.execute("""
            INSERT INTO budget_pacing
                (id, channel, period_month, week_num, week_start,
                 weekly_planned, weekly_actual, cumulative_planned, cumulative_actual,
                 pacing_rate, forecast_eom, variance_pct, pacing_status,
                 created_at, updated_at)
            SELECT id, channel, period_month, week_num, week_start,
                   weekly_planned, weekly_actual, cumulative_planned, cumulative_actual,
                   pacing_rate, forecast_eom, variance_pct, pacing_status,
                   created_at, updated_at
            FROM bp_df
        """)
        conn.commit()
    finally:
        conn.unregister("bp_df")
        conn.close()

    if verbose:
        print(f"[seed_budget_pacing] Inserted {len(df)} rows into budget_pacing")
        print(f"  Channels:          {df['channel'].nunique()}")
        print(f"  Months:            {df['period_month'].nunique()}")
        print(f"  Weeks per ch/mo:   4")
        status_counts = df["pacing_status"].value_counts()
        for status in VALID_STATUSES:
            print(f"  {status:<12} weeks: {status_counts.get(status, 0)}")
        by_ch = df.groupby("channel")[["weekly_planned", "weekly_actual"]].sum()
        print("\n  Channel pacing summary (full period):")
        for ch, row in by_ch.iterrows():
            rate = row["weekly_actual"] / row["weekly_planned"]
            print(f"    {ch:<25}  plan=${row['weekly_planned']:>12,.0f}  "
                  f"actual=${row['weekly_actual']:>12,.0f}  rate={rate:.3f}")
        print()

    return df


if __name__ == "__main__":
    seed()
