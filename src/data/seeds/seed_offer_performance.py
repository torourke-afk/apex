"""Seed: Offer Performance Data

Generates ~108 rows: 9 offers × 12 monthly periods.
Direct deposit (DD) incentive offer shows highest impact.
Funnel: eligibility → activation → fulfillment.
30/90-day P&L impact: negative at day 30 (promo cost), positive at day 90.

Idempotent: DELETE + INSERT on offer_performance.

Run:
    python -m src.data.seeds.seed_offer_performance
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
from src.data.seeds._dates import TWELVE_MONTH_STRINGS  # noqa: E402

SEED = 42
rng = np.random.default_rng(SEED)

PERIODS = TWELVE_MONTH_STRINGS

# Offer definitions: name → {elig, activ, fulfill, d30, d90} ranges
# DD incentive has highest impact (largest day90 positive return)
OFFER_SPECS = {
    "DD Incentive $300": {
        "elig": (0.55, 0.75), "activ": (0.62, 0.78), "fulfill": (0.80, 0.92),
        "d30": (-280, -220), "d90": (185, 320),
    },
    "DD Incentive $200": {
        "elig": (0.60, 0.78), "activ": (0.60, 0.76), "fulfill": (0.82, 0.93),
        "d30": (-185, -145), "d90": (130, 220),
    },
    "Savings Rate Match": {
        "elig": (0.40, 0.60), "activ": (0.45, 0.62), "fulfill": (0.70, 0.88),
        "d30": (-45, -15), "d90": (80, 160),
    },
    "Bill Pay Bonus $50": {
        "elig": (0.70, 0.85), "activ": (0.55, 0.72), "fulfill": (0.75, 0.90),
        "d30": (-48, -32), "d90": (55, 95),
    },
    "Cross-Sell CD Special": {
        "elig": (0.30, 0.48), "activ": (0.38, 0.55), "fulfill": (0.65, 0.82),
        "d30": (-30, -8), "d90": (60, 140),
    },
    "Debit Card Cashback": {
        "elig": (0.72, 0.88), "activ": (0.58, 0.74), "fulfill": (0.85, 0.95),
        "d30": (-25, -10), "d90": (40, 75),
    },
    "Digital Wallet $25": {
        "elig": (0.65, 0.80), "activ": (0.52, 0.68), "fulfill": (0.78, 0.92),
        "d30": (-24, -10), "d90": (30, 60),
    },
    "Loyalty Points 2x": {
        "elig": (0.45, 0.65), "activ": (0.42, 0.58), "fulfill": (0.72, 0.87),
        "d30": (-18, -5), "d90": (25, 55),
    },
    "Refer-a-Friend $100": {
        "elig": (0.35, 0.55), "activ": (0.32, 0.48), "fulfill": (0.70, 0.85),
        "d30": (-98, -72), "d90": (65, 130),
    },
}


def build_offer_performance() -> pd.DataFrame:
    rows = []
    now = pd.Timestamp.now()

    for offer_name, spec in OFFER_SPECS.items():
        for period_idx, period in enumerate(PERIODS):
            # Slight improvement trend per offer over time
            trend = period_idx * 0.004
            elig_noise = float(rng.normal(0, 0.02))
            activ_noise = float(rng.normal(0, 0.02))
            fulfill_noise = float(rng.normal(0, 0.015))

            eligibility = float(np.clip(
                rng.uniform(*spec["elig"]) + trend * 0.5 + elig_noise, 0.05, 0.99
            ))
            activation = float(np.clip(
                rng.uniform(*spec["activ"]) + trend + activ_noise, 0.05, 0.99
            ))
            fulfillment = float(np.clip(
                rng.uniform(*spec["fulfill"]) + trend * 0.3 + fulfill_noise, 0.05, 0.99
            ))

            day_30 = float(rng.uniform(*spec["d30"]) * (1 + rng.normal(0, 0.05)))
            day_90 = float(rng.uniform(*spec["d90"]) * (1 + rng.normal(0, 0.05)))

            rows.append({
                "id":               str(uuid.uuid4()),
                "offer_name":       offer_name,
                "eligibility_rate": round(eligibility, 4),
                "activation_rate":  round(activation, 4),
                "fulfillment_rate": round(fulfillment, 4),
                "day_30_impact":    round(day_30, 4),
                "day_90_impact":    round(day_90, 4),
                "period":           period,
                "created_at":       now,
                "updated_at":       now,
            })

    return pd.DataFrame(rows)


OFFER_SCHEMA = DataFrameSchema(
    {
        "id":               Column(str, nullable=False),
        "offer_name":       Column(str, nullable=False),
        "eligibility_rate": Column(float, Check.in_range(0.0, 1.0)),
        "activation_rate":  Column(float, Check.in_range(0.0, 1.0)),
        "fulfillment_rate": Column(float, Check.in_range(0.0, 1.0)),
        "day_30_impact":    Column(float),  # can be negative (promo cost)
        "day_90_impact":    Column(float),  # should be positive
        "period":           Column(str, nullable=False),
    },
    checks=[
        Check(lambda df: len(df) == 108, error="Expected exactly 108 rows (9 offers × 12 periods)"),
        Check(lambda df: df["offer_name"].nunique() == 9, error="Expected 9 unique offers"),
        # DD incentives should have highest avg day90 impact
        Check(
            lambda df: (
                df[df["offer_name"].str.startswith("DD Incentive")]["day_90_impact"].mean()
                > df[~df["offer_name"].str.startswith("DD Incentive")]["day_90_impact"].mean()
            ),
            error="DD Incentive offers should have highest average day_90_impact",
        ),
        # Day 30 should be negative for most offers (promo cost during early period)
        Check(
            lambda df: (df["day_30_impact"] < 0).mean() > 0.80,
            error="At least 80% of day_30_impact values should be negative (promo cost)",
        ),
        # Day 90 should generally be positive (ROI materializes)
        Check(
            lambda df: (df["day_90_impact"] > 0).mean() > 0.90,
            error="At least 90% of day_90_impact values should be positive",
        ),
    ],
    coerce=True,
)


def seed(verbose: bool = True) -> pd.DataFrame:
    df = build_offer_performance()

    for col in ("eligibility_rate", "activation_rate", "fulfillment_rate",
                "day_30_impact", "day_90_impact"):
        df[col] = df[col].astype(float)

    OFFER_SCHEMA.validate(df)

    conn = get_connection()
    try:
        conn.execute("DELETE FROM offer_performance")
        conn.register("offer_df", df)
        conn.execute("""
            INSERT INTO offer_performance
                (id, offer_name, eligibility_rate, activation_rate, fulfillment_rate,
                 day_30_impact, day_90_impact, period, created_at, updated_at)
            SELECT id, offer_name, eligibility_rate, activation_rate, fulfillment_rate,
                   day_30_impact, day_90_impact, period, created_at, updated_at
            FROM offer_df
        """)
        conn.commit()
    finally:
        try:
            conn.unregister("offer_df")
        except Exception:
            pass
        conn.close()

    if verbose:
        print(f"[seed_offer_performance] Inserted {len(df)} rows into offer_performance")
        summary = (
            df.groupby("offer_name")
            .agg(avg_d30=("day_30_impact", "mean"), avg_d90=("day_90_impact", "mean"),
                 avg_activ=("activation_rate", "mean"))
            .sort_values("avg_d90", ascending=False)
        )
        for name, row in summary.iterrows():
            print(f"  {name:<28} d30={row['avg_d30']:>+7.0f}  "
                  f"d90={row['avg_d90']:>+7.0f}  "
                  f"activ={row['avg_activ']:.1%}")

    return df


if __name__ == "__main__":
    seed()
