"""Seed: Channel Mix Defaults & Projection Coefficients

Generates 48 rows (6 budget channels × 8 products) defining the baseline
channel mix percentages and projection coefficients used by the Spend
Allocation slider panel.

Targets the `channel_mix` table (APE-62 schema):
    id, channel, product, baseline_mix_pct,
    cpa_target, roas_target, conversion_rate_base, growth_coeff,
    q1_seasonality, q2_seasonality, q3_seasonality, q4_seasonality,
    budget_elasticity, saturation_point, created_at, updated_at

Channel mix constraints (from APE-13 slider spec):
  - CTV/OLV (brand_media sub-channel proxy): slider range 30–50%
  - Paid Social: slider range 25–50%
  - Audio (streaming_audio): slider range 5–20%
  - SEO/AEO: 3–12%
  - Conversion/Testing: 2–8%
  - High-Value Overlay: 5–15%

Since the table uses the 6 budget-level channels, baseline_mix_pct is the
fractional share of that channel within the overall brand media pool.  The
6 channels must sum to 1.0 per product.

Projection coefficients:
  - growth_coeff: incremental conversions per $1K additional spend
  - budget_elasticity: % change in conversions per 1% budget change (0–1)
  - saturation_point: spend level at which marginal returns flatten ($)
  - seasonal factors (q1–q4): multiplicative adjustments vs. flat baseline

Idempotent: DELETE + INSERT.

Run:
    python -m src.data.seeds.seed_channel_mix
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

SEED = 55
rng = np.random.default_rng(SEED)

VALID_CHANNELS = [
    "brand_media",
    "paid_search",
    "paid_social",
    "high_value_overlay",
    "seo_aeo",
    "conversion_testing",
]

VALID_PRODUCTS = [
    "checking",
    "savings",
    "credit_card",
    "mortgage",
    "auto_loan",
    "personal_loan",
    "cd",
    "money_market",
]

# Baseline channel mix by product (rows must sum to 1.0 per product).
# Values represent fractional share of overall budget allocated to each channel.
#
# Design rationale:
#   - Checking/Savings: brand-heavy (awareness play)
#   - Credit card: performance-heavy (direct response)
#   - Mortgage: high-value overlay + brand mix
#   - Auto loan: paid social + SEM mix
#   - CD/Money market: SEO-heavy + email (older demographic, lower brand media)
#
# Layout: brand_media, paid_search, paid_social, high_value_overlay, seo_aeo, conversion_testing
BASELINE_MIX = {
    "checking":      [0.40, 0.25, 0.15, 0.12, 0.05, 0.03],
    "savings":       [0.38, 0.26, 0.16, 0.11, 0.06, 0.03],
    "credit_card":   [0.30, 0.32, 0.20, 0.09, 0.05, 0.04],
    "mortgage":      [0.35, 0.22, 0.14, 0.20, 0.05, 0.04],
    "auto_loan":     [0.33, 0.28, 0.19, 0.10, 0.06, 0.04],
    "personal_loan": [0.28, 0.33, 0.20, 0.10, 0.05, 0.04],
    "cd":            [0.32, 0.24, 0.13, 0.12, 0.12, 0.07],
    "money_market":  [0.30, 0.25, 0.12, 0.13, 0.13, 0.07],
}

# Channel performance benchmarks (base values, product-level noise added later)
# (cpa_target, roas_target, conversion_rate_base)
CHANNEL_BENCHMARKS = {
    "brand_media":        (520.0,  2.8,  0.0030),
    "paid_search":        (185.0,  5.2,  0.0480),
    "paid_social":        (210.0,  4.1,  0.0320),
    "high_value_overlay": (290.0,  3.9,  0.0210),
    "seo_aeo":            (145.0,  6.8,  0.0550),
    "conversion_testing": (165.0,  5.5,  0.0420),
}

# Growth coefficient (incremental conversions per $1K spend) — higher for performance channels
CHANNEL_GROWTH_COEFF = {
    "brand_media":        0.0012,
    "paid_search":        0.0085,
    "paid_social":        0.0062,
    "high_value_overlay": 0.0048,
    "seo_aeo":            0.0095,
    "conversion_testing": 0.0075,
}

# Saturation point ($) — spend level where marginal returns flatten significantly
CHANNEL_SATURATION = {
    "brand_media":        4_200_000,
    "paid_search":        2_800_000,
    "paid_social":        2_000_000,
    "high_value_overlay": 1_500_000,
    "seo_aeo":              600_000,
    "conversion_testing":   380_000,
}

# Budget elasticity (0–1): sensitivity of conversions to budget changes
# 1.0 = fully elastic; 0.0 = no response to budget changes
CHANNEL_ELASTICITY = {
    "brand_media":        0.55,
    "paid_search":        0.82,
    "paid_social":        0.75,
    "high_value_overlay": 0.65,
    "seo_aeo":            0.42,
    "conversion_testing": 0.72,
}

# Seasonal index (q1, q2, q3, q4) relative to 1.0 baseline
# >1.0 means above-average performance in that quarter
CHANNEL_SEASONALITY = {
    "brand_media":        (0.92, 0.98, 1.05, 1.15),
    "paid_search":        (1.08, 0.96, 0.94, 1.12),
    "paid_social":        (0.95, 1.02, 1.08, 1.05),
    "high_value_overlay": (1.05, 0.98, 0.96, 1.08),
    "seo_aeo":            (1.02, 1.00, 0.98, 1.00),
    "conversion_testing": (0.90, 0.98, 1.08, 1.12),
}

# Product CPA multipliers (checking = 1.0 baseline)
PRODUCT_CPA_MULT = {
    "checking":      1.00,
    "savings":       0.95,
    "credit_card":   1.30,
    "mortgage":      3.20,
    "auto_loan":     2.10,
    "personal_loan": 1.40,
    "cd":            0.85,
    "money_market":  0.90,
}


# ---------------------------------------------------------------------------
# Row builder
# ---------------------------------------------------------------------------

def build_rows() -> List[dict]:
    """Build 48 channel mix rows (6 channels × 8 products)."""
    rows: List[dict] = []
    now = pd.Timestamp.now()

    for product in VALID_PRODUCTS:
        mix_weights = BASELINE_MIX[product]
        cpa_mult = PRODUCT_CPA_MULT[product]

        for ch_idx, channel in enumerate(VALID_CHANNELS):
            baseline_mix_pct = mix_weights[ch_idx]

            cpa_base, roas_base, cvr_base = CHANNEL_BENCHMARKS[channel]

            # Add small product-level noise to performance metrics
            cpa_target = round(cpa_base * cpa_mult * float(rng.uniform(0.94, 1.06)), 2)
            roas_target = round(roas_base * float(rng.uniform(0.93, 1.07)), 4)
            cvr_base_adj = float(np.clip(cvr_base * float(rng.uniform(0.90, 1.10)), 0.0001, 0.20))

            growth_coeff = round(
                CHANNEL_GROWTH_COEFF[channel] * float(rng.uniform(0.95, 1.05)), 6
            )
            elasticity = round(
                float(np.clip(CHANNEL_ELASTICITY[channel] + rng.uniform(-0.03, 0.03), 0.10, 0.99)),
                4
            )
            saturation = round(
                CHANNEL_SATURATION[channel] * float(rng.uniform(0.95, 1.05)), 2
            )

            q1, q2, q3, q4 = CHANNEL_SEASONALITY[channel]

            rows.append({
                "id":                   str(uuid.uuid4()),
                "channel":              channel,
                "product":              product,
                "baseline_mix_pct":     round(baseline_mix_pct, 4),
                "cpa_target":           cpa_target,
                "roas_target":          roas_target,
                "conversion_rate_base": round(cvr_base_adj, 6),
                "growth_coeff":         growth_coeff,
                "q1_seasonality":       round(q1 * float(rng.uniform(0.98, 1.02)), 4),
                "q2_seasonality":       round(q2 * float(rng.uniform(0.98, 1.02)), 4),
                "q3_seasonality":       round(q3 * float(rng.uniform(0.98, 1.02)), 4),
                "q4_seasonality":       round(q4 * float(rng.uniform(0.98, 1.02)), 4),
                "budget_elasticity":    elasticity,
                "saturation_point":     saturation,
                "created_at":           now,
                "updated_at":           now,
            })

    return rows


# ---------------------------------------------------------------------------
# Pandera schema
# ---------------------------------------------------------------------------

CHANNEL_MIX_SCHEMA = DataFrameSchema(
    {
        "id":                   Column(str, nullable=False),
        "channel":              Column(str, Check.isin(VALID_CHANNELS), nullable=False),
        "product":              Column(str, Check.isin(VALID_PRODUCTS), nullable=False),
        "baseline_mix_pct":     Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "cpa_target":           Column(float, Check.greater_than(0), nullable=False),
        "roas_target":          Column(float, Check.greater_than(0), nullable=False),
        "conversion_rate_base": Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "growth_coeff":         Column(float, Check.greater_than(0), nullable=False),
        "q1_seasonality":       Column(float, Check.in_range(0.5, 2.0), nullable=False),
        "q2_seasonality":       Column(float, Check.in_range(0.5, 2.0), nullable=False),
        "q3_seasonality":       Column(float, Check.in_range(0.5, 2.0), nullable=False),
        "q4_seasonality":       Column(float, Check.in_range(0.5, 2.0), nullable=False),
        "budget_elasticity":    Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "saturation_point":     Column(float, Check.greater_than(0), nullable=False),
    },
    checks=[
        Check(
            lambda df: len(df) == 48,
            error="channel_mix: expected exactly 48 rows (6 channels × 8 products)",
        ),
        Check(
            lambda df: df["channel"].nunique() == 6,
            error="channel_mix: expected 6 distinct channels",
        ),
        Check(
            lambda df: df["product"].nunique() == 8,
            error="channel_mix: expected 8 distinct products",
        ),
        Check(
            lambda df: df.groupby("product")["baseline_mix_pct"]
                         .sum()
                         .apply(lambda s: abs(s - 1.0) < 0.001)
                         .all(),
            error="channel_mix: baseline_mix_pct must sum to 1.0 per product (±0.001)",
        ),
    ],
    coerce=True,
)


# ---------------------------------------------------------------------------
# Seed function
# ---------------------------------------------------------------------------

def seed(verbose: bool = True) -> pd.DataFrame:
    """Build and insert channel mix seed data into DuckDB. Idempotent."""
    rows = build_rows()
    df = pd.DataFrame(rows)

    for col in ["baseline_mix_pct", "cpa_target", "roas_target", "conversion_rate_base",
                "growth_coeff", "q1_seasonality", "q2_seasonality",
                "q3_seasonality", "q4_seasonality", "budget_elasticity", "saturation_point"]:
        df[col] = df[col].astype(float)

    CHANNEL_MIX_SCHEMA.validate(df)

    conn = get_connection()
    try:
        conn.execute("DELETE FROM channel_mix")
        conn.register("cm_df", df)
        conn.execute("""
            INSERT INTO channel_mix
                (id, channel, product, baseline_mix_pct,
                 cpa_target, roas_target, conversion_rate_base, growth_coeff,
                 q1_seasonality, q2_seasonality, q3_seasonality, q4_seasonality,
                 budget_elasticity, saturation_point, created_at, updated_at)
            SELECT id, channel, product, baseline_mix_pct,
                   cpa_target, roas_target, conversion_rate_base, growth_coeff,
                   q1_seasonality, q2_seasonality, q3_seasonality, q4_seasonality,
                   budget_elasticity, saturation_point, created_at, updated_at
            FROM cm_df
        """)
        conn.commit()
    finally:
        conn.unregister("cm_df")
        conn.close()

    if verbose:
        print(f"[seed_channel_mix] Inserted {len(df)} rows into channel_mix")
        print(f"  Channels:  {df['channel'].nunique()}")
        print(f"  Products:  {df['product'].nunique()}")
        print("\n  Baseline mix by channel (avg across products):")
        avg_mix = df.groupby("channel")["baseline_mix_pct"].mean().sort_values(ascending=False)
        for ch, pct in avg_mix.items():
            print(f"    {ch:<25}  {pct:.1%}")
        print("\n  Mix sum per product (should all be 1.000):")
        sums = df.groupby("product")["baseline_mix_pct"].sum()
        for prod, s in sums.items():
            ok = "OK" if abs(s - 1.0) < 0.001 else "FAIL"
            print(f"    {prod:<15}  {s:.4f}  [{ok}]")
        print()

    return df


if __name__ == "__main__":
    seed()
