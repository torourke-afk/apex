"""Seed: BEI (Bank Engagement Index) Scores

Generates 36 rows: 3 market tiers × 12 months.
Score ranges: Tier 1: 70-85, Tier 2: 50-70, Tier 3: 35-55.
Upward trend applied across the 12-month window.
Composite validates against the weighted formula in BEIScore model.

Idempotent: DELETE + INSERT on bei_scores.

Run:
    python -m src.data.seeds.seed_bei_scores
"""

from __future__ import annotations

import os
import sys
import uuid
from decimal import Decimal, ROUND_HALF_UP

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

PERIODS = [
    "2025-05", "2025-06", "2025-07", "2025-08", "2025-09", "2025-10",
    "2025-11", "2025-12", "2026-01", "2026-02", "2026-03", "2026-04",
]

# Tier definitions: (center_score, half_range)
TIER_RANGES = {
    "tier_1": (77.5, 7.5),    # 70–85
    "tier_2": (60.0, 10.0),   # 50–70
    "tier_3": (45.0, 10.0),   # 35–55
}

# Component weights — must match BEIScore model
WEIGHTS = {
    "direct_deposit_score":    Decimal("0.35"),
    "digital_adoption_score":  Decimal("0.25"),
    "cross_sell_score":        Decimal("0.20"),
    "product_depth_score":     Decimal("0.12"),
    "engagement_score":        Decimal("0.08"),
}

# Monthly upward trend (score points per month)
TREND_PER_MONTH = 0.25


def _component_scores(tier: str, period_idx: int) -> dict[str, float]:
    """Generate component scores for a tier/period with trend and noise."""
    center, half = TIER_RANGES[tier]
    trend = period_idx * TREND_PER_MONTH

    scores = {}
    for component in WEIGHTS:
        # Slightly different center per component ±5 pts
        comp_center = center + rng.uniform(-5, 5) + trend
        noise = float(rng.normal(0, 1.5))
        raw = comp_center + noise
        scores[component] = float(np.clip(raw, 0, 100))

    return scores


def _compute_composite(scores: dict[str, float]) -> float:
    """Compute weighted composite, matching BEIScore formula exactly."""
    total = Decimal("0")
    for field, weight in WEIGHTS.items():
        total += Decimal(str(round(scores[field], 2))) * weight
    return float(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def build_bei_scores() -> pd.DataFrame:
    rows = []
    now = pd.Timestamp.now()

    for tier in ["tier_1", "tier_2", "tier_3"]:
        for period_idx, period in enumerate(PERIODS):
            scores = _component_scores(tier, period_idx)
            composite = _compute_composite(scores)

            rows.append({
                "id":                     str(uuid.uuid4()),
                "market_tier":            tier,
                "period":                 period,
                "direct_deposit_score":   round(scores["direct_deposit_score"], 2),
                "digital_adoption_score": round(scores["digital_adoption_score"], 2),
                "cross_sell_score":       round(scores["cross_sell_score"], 2),
                "product_depth_score":    round(scores["product_depth_score"], 2),
                "engagement_score":       round(scores["engagement_score"], 2),
                "composite_score":        composite,
                "created_at":             now,
                "updated_at":             now,
            })

    return pd.DataFrame(rows)


BEI_SCHEMA = DataFrameSchema(
    {
        "id":                     Column(str, nullable=False),
        "market_tier":            Column(str, Check.isin(["tier_1", "tier_2", "tier_3"])),
        "period":                 Column(str, nullable=False),
        "direct_deposit_score":   Column(float, Check.in_range(0, 100)),
        "digital_adoption_score": Column(float, Check.in_range(0, 100)),
        "cross_sell_score":       Column(float, Check.in_range(0, 100)),
        "product_depth_score":    Column(float, Check.in_range(0, 100)),
        "engagement_score":       Column(float, Check.in_range(0, 100)),
        "composite_score":        Column(float, Check.in_range(0, 100)),
    },
    checks=[
        Check(lambda df: len(df) == 36, error="Expected exactly 36 rows (3 tiers × 12 months)"),
        Check(
            lambda df: df.groupby("market_tier")["composite_score"].mean()["tier_1"]
            > df.groupby("market_tier")["composite_score"].mean()["tier_2"]
            > df.groupby("market_tier")["composite_score"].mean()["tier_3"],
            error="Tier 1 > Tier 2 > Tier 3 composite ordering violated",
        ),
        # Tier range checks
        Check(
            lambda df: (df[df["market_tier"] == "tier_1"]["composite_score"].between(60, 100)).all(),
            error="Tier 1 composites out of expected range",
        ),
        Check(
            lambda df: (df[df["market_tier"] == "tier_3"]["composite_score"].between(25, 65)).all(),
            error="Tier 3 composites out of expected range",
        ),
        # Upward trend: last 3 months avg > first 3 months avg per tier
        Check(
            lambda df: all(
                df[df["market_tier"] == tier].sort_values("period")
                .tail(3)["composite_score"].mean()
                > df[df["market_tier"] == tier].sort_values("period")
                .head(3)["composite_score"].mean()
                for tier in ["tier_1", "tier_2", "tier_3"]
            ),
            error="Upward trend not present across all tiers",
        ),
    ],
    coerce=True,
)


def seed(verbose: bool = True) -> pd.DataFrame:
    df = build_bei_scores()

    for col in ("direct_deposit_score", "digital_adoption_score", "cross_sell_score",
                "product_depth_score", "engagement_score", "composite_score"):
        df[col] = df[col].astype(float)

    BEI_SCHEMA.validate(df)

    conn = get_connection()
    try:
        conn.execute("DELETE FROM bei_scores")
        conn.register("bei_df", df)
        conn.execute("""
            INSERT INTO bei_scores
                (id, market_tier, period, direct_deposit_score, digital_adoption_score,
                 cross_sell_score, product_depth_score, engagement_score,
                 composite_score, created_at, updated_at)
            SELECT id, market_tier, period, direct_deposit_score, digital_adoption_score,
                   cross_sell_score, product_depth_score, engagement_score,
                   composite_score, created_at, updated_at
            FROM bei_df
        """)
        conn.commit()
    finally:
        try:
            conn.unregister("bei_df")
        except Exception:
            pass
        conn.close()

    if verbose:
        print(f"[seed_bei_scores] Inserted {len(df)} rows into bei_scores")
        for tier in ["tier_1", "tier_2", "tier_3"]:
            grp = df[df["market_tier"] == tier].sort_values("period")
            print(f"  {tier}: composite {grp['composite_score'].min():.1f}–"
                  f"{grp['composite_score'].max():.1f} "
                  f"(trend: {grp.head(3)['composite_score'].mean():.1f} → "
                  f"{grp.tail(3)['composite_score'].mean():.1f})")

    return df


if __name__ == "__main__":
    seed()
