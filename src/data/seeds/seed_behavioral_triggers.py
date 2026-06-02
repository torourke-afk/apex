"""Seed: Behavioral Trigger Performance Data

Generates 312 rows: 6 triggers × 52 weeks (mapped to 12 monthly periods).
Realistic weekly volumes and conversion rates per trigger type.

Idempotent: DELETE + INSERT on behavioral_triggers.

Run:
    python -m src.data.seeds.seed_behavioral_triggers
"""

from __future__ import annotations

import os
import sys
import uuid

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

SEED = 42
rng = np.random.default_rng(SEED)

# 52 weeks mapped to 12 monthly periods (ceil division, last period gets extras)
WEEKS_PER_PERIOD = [4, 4, 5, 4, 4, 4, 4, 5, 4, 4, 4, 6]  # sums to 52
assert sum(WEEKS_PER_PERIOD) == 52

PERIODS = [
    "2025-05", "2025-06", "2025-07", "2025-08", "2025-09", "2025-10",
    "2025-11", "2025-12", "2026-01", "2026-02", "2026-03", "2026-04",
]

# Trigger definitions: name → (condition, action, weekly_volume_range, cvr_range)
TRIGGERS = {
    "dd_setup_nudge": (
        "No direct deposit within 14 days of account open",
        "Send personalized DD setup guide + $50 reward reminder",
        (8_000, 14_000),
        (0.18, 0.28),
    ),
    "login_gap_reactivation": (
        "No digital login for 30+ consecutive days",
        "Push notification + email with top feature highlights",
        (12_000, 20_000),
        (0.09, 0.16),
    ),
    "low_balance_alert": (
        "Balance drops below $100 with no pending transfers",
        "SMS alert with savings transfer CTA",
        (18_000, 28_000),
        (0.12, 0.20),
    ),
    "cross_sell_savings": (
        "Checking-only customer with 3+ months tenure and avg balance > $1,500",
        "Targeted savings account offer with rate highlight",
        (5_000, 9_000),
        (0.22, 0.34),
    ),
    "bill_pay_onboarding": (
        "Account open 7–21 days, no bill pay enrolled",
        "In-app guided bill pay setup walkthrough",
        (6_500, 11_000),
        (0.25, 0.38),
    ),
    "churn_risk_winback": (
        "Declining balance trend 3 consecutive months + no new products",
        "Relationship manager outreach + retention offer",
        (2_500, 5_000),
        (0.14, 0.24),
    ),
}


def build_behavioral_triggers() -> pd.DataFrame:
    rows = []
    now = pd.Timestamp.now()
    week_num = 1

    for period_idx, (period, n_weeks) in enumerate(zip(PERIODS, WEEKS_PER_PERIOD)):
        # Slight seasonal lift in Q4/Q1 for volume
        seasonal_mult = 1.10 if period in ("2025-11", "2025-12", "2026-01") else 1.0
        # Gradual CVR improvement over time (optimization trend)
        cvr_trend = period_idx * 0.003

        for _ in range(n_weeks):
            for trigger_name, (condition, action, vol_range, cvr_range) in TRIGGERS.items():
                vol_noise = float(rng.lognormal(0, 0.12))
                volume = int(
                    rng.uniform(*vol_range) * seasonal_mult * vol_noise
                )
                cvr = float(np.clip(
                    rng.uniform(*cvr_range) + cvr_trend + rng.normal(0, 0.01),
                    0.05,
                    0.60,
                ))
                rows.append({
                    "id":              str(uuid.uuid4()),
                    "trigger_name":    trigger_name,
                    "condition":       condition,
                    "action":          action,
                    "volume_per_week": volume,
                    "conversion_rate": round(cvr, 4),
                    "period":          period,
                    "week_num":        week_num,
                    "created_at":      now,
                    "updated_at":      now,
                })
            week_num += 1

    return pd.DataFrame(rows)


TRIGGER_SCHEMA = DataFrameSchema(
    {
        "id":              Column(str, nullable=False),
        "trigger_name":    Column(str, Check.isin(list(TRIGGERS.keys()))),
        "condition":       Column(str, nullable=False),
        "action":          Column(str, nullable=False),
        "volume_per_week": Column(int, Check.greater_than(0)),
        "conversion_rate": Column(float, Check.in_range(0.0, 1.0)),
        "period":          Column(str, nullable=False),
    },
    checks=[
        Check(lambda df: len(df) == 312, error="Expected exactly 312 rows (6 triggers × 52 weeks)"),
        Check(lambda df: df["trigger_name"].nunique() == 6, error="Expected 6 unique triggers"),
        Check(lambda df: df["period"].nunique() == 12, error="Expected 12 unique periods"),
    ],
    coerce=True,
)

_DDL_ALTER = """
ALTER TABLE behavioral_triggers ADD COLUMN IF NOT EXISTS week_num INTEGER
"""


def seed(verbose: bool = True) -> pd.DataFrame:
    df = build_behavioral_triggers()

    df["conversion_rate"] = df["conversion_rate"].astype(float)
    df["volume_per_week"] = df["volume_per_week"].astype(int)

    TRIGGER_SCHEMA.validate(df)

    conn = get_connection()
    try:
        # Migration-safe: add week_num column if missing
        existing_cols = {
            row[0].lower()
            for row in conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'behavioral_triggers'"
            ).fetchall()
        }
        if "week_num" not in existing_cols:
            conn.execute("ALTER TABLE behavioral_triggers ADD COLUMN week_num INTEGER")
            if verbose:
                print("[seed_behavioral_triggers] Migration: added week_num column")

        conn.execute("DELETE FROM behavioral_triggers")
        conn.register("trig_df", df)
        conn.execute("""
            INSERT INTO behavioral_triggers
                (id, trigger_name, condition, action, volume_per_week,
                 conversion_rate, period, week_num, created_at, updated_at)
            SELECT id, trigger_name, condition, action, volume_per_week,
                   conversion_rate, period, week_num, created_at, updated_at
            FROM trig_df
        """)
        conn.commit()
    finally:
        try:
            conn.unregister("trig_df")
        except Exception:
            pass
        conn.close()

    if verbose:
        print(f"[seed_behavioral_triggers] Inserted {len(df)} rows into behavioral_triggers")
        summary = (
            df.groupby("trigger_name")
            .agg(avg_volume=("volume_per_week", "mean"), avg_cvr=("conversion_rate", "mean"))
            .sort_values("avg_cvr", ascending=False)
        )
        for name, row in summary.iterrows():
            print(f"  {name:<28} vol={row['avg_volume']:>7,.0f}/wk  "
                  f"cvr={row['avg_cvr']:.1%}")

    return df


if __name__ == "__main__":
    seed()
