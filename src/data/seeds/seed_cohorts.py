"""Seed: individual cohort member rows with PFI milestones (APE-48 spec).

Revised from APE-40 to match APE-48 / APE-10 spec deltas:
  - MOB6 retention: 70-80%  (was 55-65%)
  - MOB12 retention: 65-75% (was 40-50%)
  - PFI milestone completion rates per spec
  - Quality score distribution: 30% high, 45% medium, 25% low
  - Offer type distribution:    40% cash_bonus, 25% stacked, 35% no_offer
  - >=5,000 individual cohort member rows (was >=10k cohort-month aggregate rows)

One row per cohort member:
  name     = "{cohort_label} | PFI Member {member_id:05d}"
  segment  = channel
  size     = 1 (individual member)
  criteria = {
    "quality_score":      "high" | "medium" | "low",
    "offer_type":         "cash_bonus" | "stacked" | "no_offer",
    "mob6_retained":      true/false,
    "mob12_retained":     true/false,
    "channel":            "paid_search" | ...,
    "product":            "checking" | ...,
    "direct_deposit_d30": true/false,
    "bill_pay_d60":       true/false,
    "debit_card_d14":     true/false,
    "digital_wallet_d30": true/false,
    "p2p_payments_d60":   true/false,
    "cross_sell_d90":     true/false
  }

Idempotent: deletes rows WHERE name LIKE '% | PFI Member %' before re-inserting.
"""

import json
import numpy as np
import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema, Check
import duckdb
from datetime import date
from dateutil.relativedelta import relativedelta

from src.config.settings import DB_PATH, DB_URL, is_dev_mode

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SEED = 42

NUM_COHORTS = 40           # monthly cohorts (rolling 40-month window)
MEMBERS_PER_COHORT = 140   # 40 × 140 = 5,600 rows  (≥ 5,000 spec)

CHANNELS = ["paid_search", "organic", "email", "direct_mail", "referral"]
PRODUCTS = ["checking", "savings", "credit_card", "mortgage", "auto_loan"]

QUALITY_SCORES = ["high", "medium", "low"]
QUALITY_PROBS  = [0.30,   0.45,     0.25]

OFFER_TYPES = ["cash_bonus", "stacked", "no_offer"]
OFFER_PROBS = [0.40,         0.25,      0.35]

# MOB retention ranges (spec: MOB6 70-80%, MOB12 65-75%)
MOB6_RANGE  = (0.70, 0.80)
MOB12_RANGE = (0.65, 0.75)

# PFI milestone base completion rates: (low_bound, high_bound)
PFI_MILESTONES = {
    "direct_deposit_d30": (0.35, 0.55),
    "bill_pay_d60":        (0.20, 0.35),
    "debit_card_d14":      (0.55, 0.75),
    "digital_wallet_d30":  (0.15, 0.30),
    "p2p_payments_d60":    (0.15, 0.25),
    "cross_sell_d90":      (0.15, 0.30),
}

# Additive offsets applied to PFI milestone rates by quality score
QUALITY_MILESTONE_OFFSET = {
    "high":   +0.05,
    "medium":  0.00,
    "low":    -0.05,
}

# Additive offsets applied to MOB6/MOB12 rates by quality score
QUALITY_RETENTION_OFFSET = {
    "high":   +0.03,
    "medium":  0.00,
    "low":    -0.04,
}

# Additive offsets to direct_deposit + bill_pay by offer type
OFFER_DD_BILLPAY_OFFSET = {
    "cash_bonus":  +0.05,
    "stacked":     +0.03,
    "no_offer":     0.00,
}

# ---------------------------------------------------------------------------
# Pandera schema
# ---------------------------------------------------------------------------
SCHEMA = DataFrameSchema(
    {
        "name":           Column(str, nullable=False),
        "segment":        Column(str, Check.isin(CHANNELS), nullable=False),
        "product":        Column(str, Check.isin(PRODUCTS), nullable=False),
        "quality_score":  Column(str, Check.isin(QUALITY_SCORES), nullable=False),
        "offer_type":     Column(str, Check.isin(OFFER_TYPES), nullable=False),
        "mob6_retained":  Column(bool, nullable=False),
        "mob12_retained": Column(bool, nullable=False),
        "size":           Column(int, Check.equal_to(1), nullable=False),
        "period_start":   Column(pa.DateTime, nullable=False),
        "period_end":     Column(pa.DateTime, nullable=False),
    },
    checks=[
        Check(
            lambda df: (df["mob6_retained"].mean() >= 0.70) and
                       (df["mob6_retained"].mean() <= 0.80),
            error="MOB6 retention must be in [70%, 80%]",
        ),
        Check(
            lambda df: (df["mob12_retained"].mean() >= 0.65) and
                       (df["mob12_retained"].mean() <= 0.75),
            error="MOB12 retention must be in [65%, 75%]",
        ),
        Check(
            lambda df: (df["quality_score"] == "high").mean() >= 0.25,
            error="high quality score share must be >= 25%",
        ),
        Check(
            lambda df: len(df) >= 5_000,
            error="Must have >= 5,000 rows",
        ),
    ],
    coerce=True,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _bernoulli(rng: np.random.Generator, p: float) -> bool:
    return bool(rng.random() < float(np.clip(p, 0.0, 1.0)))


def _pfi_rate(
    milestone: str,
    quality: str,
    offer: str,
    rng: np.random.Generator,
) -> float:
    lo, hi = PFI_MILESTONES[milestone]
    base = rng.uniform(lo, hi)
    base += QUALITY_MILESTONE_OFFSET[quality]
    if milestone in ("direct_deposit_d30", "bill_pay_d60"):
        base += OFFER_DD_BILLPAY_OFFSET[offer]
    return float(np.clip(base, 0.0, 1.0))


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------
def generate_cohort_data(rng: np.random.Generator) -> pd.DataFrame:
    today = date.today().replace(day=1)
    rows: list[dict] = []
    global_member_id = 1

    for cohort_idx in range(NUM_COHORTS):
        cohort_date = today - relativedelta(months=NUM_COHORTS - 1 - cohort_idx)
        cohort_label = cohort_date.strftime("%Y-%m")
        # period_end = 12 months after cohort start (full observation window)
        period_end = cohort_date + relativedelta(months=12)

        # Cohort-level base retention rates (drawn once per cohort)
        cohort_mob6  = rng.uniform(*MOB6_RANGE)
        cohort_mob12 = rng.uniform(MOB12_RANGE[0], min(MOB12_RANGE[1], cohort_mob6))

        for _ in range(MEMBERS_PER_COHORT):
            channel = rng.choice(CHANNELS)
            product = rng.choice(PRODUCTS)
            quality = rng.choice(QUALITY_SCORES, p=QUALITY_PROBS)
            offer   = rng.choice(OFFER_TYPES,   p=OFFER_PROBS)

            # Per-member retention (adjusted by quality score)
            q_ret = QUALITY_RETENTION_OFFSET[quality]
            mob6_rate  = float(np.clip(cohort_mob6  + q_ret, 0.0, 1.0))
            mob12_rate = float(np.clip(cohort_mob12 + q_ret, 0.0, 1.0))

            mob6_ret  = _bernoulli(rng, mob6_rate)
            # Can only be retained at MOB12 if retained at MOB6
            mob12_ret = mob6_ret and _bernoulli(
                rng, mob12_rate / mob6_rate if mob6_rate > 0 else 0.0
            )

            # PFI milestones (per-member using cohort-averaged rates)
            pfi = {
                m: _bernoulli(rng, _pfi_rate(m, quality, offer, rng))
                for m in PFI_MILESTONES
            }

            rows.append(
                {
                    "name":           f"{cohort_label} | PFI Member {global_member_id:05d}",
                    "segment":        channel,
                    "product":        product,
                    "quality_score":  quality,
                    "offer_type":     offer,
                    "mob6_retained":  mob6_ret,
                    "mob12_retained": mob12_ret,
                    "size":           1,
                    "period_start":   pd.Timestamp(cohort_date),
                    "period_end":     pd.Timestamp(period_end),
                    # PFI columns (for criteria JSON construction)
                    **{f"pfi_{k}": v for k, v in pfi.items()},
                }
            )
            global_member_id += 1

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# DB write
# ---------------------------------------------------------------------------
def get_connection() -> duckdb.DuckDBPyConnection:
    if is_dev_mode():
        return duckdb.connect(DB_PATH)
    return duckdb.connect(":memory:")


def seed(conn: duckdb.DuckDBPyConnection | None = None) -> pd.DataFrame:
    """Generate PFI cohort member data, validate, and write to the cohorts table."""
    rng = np.random.default_rng(SEED)
    df = generate_cohort_data(rng)

    # Separate PFI columns from schema columns for validation
    pfi_cols = [c for c in df.columns if c.startswith("pfi_")]
    validate_df = df.drop(columns=pfi_cols)
    validated = SCHEMA.validate(validate_df)

    close_conn = conn is None
    if conn is None:
        conn = get_connection()

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cohorts (
                id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name         VARCHAR NOT NULL,
                segment      VARCHAR,
                criteria     JSON,
                size         INTEGER,
                period_start DATE,
                period_end   DATE,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Idempotent: remove previously seeded APE-48 PFI member rows
        conn.execute("DELETE FROM cohorts WHERE name LIKE '% | PFI Member %'")

        # Build criteria JSON per member (merge validated columns + PFI booleans)
        full_df = validated.copy()
        for col in pfi_cols:
            full_df[col] = df[col].values

        milestone_map = {
            f"pfi_{m}": m for m in PFI_MILESTONES
        }

        full_df["criteria"] = full_df.apply(
            lambda r: json.dumps(
                {
                    "quality_score":   r["quality_score"],
                    "offer_type":      r["offer_type"],
                    "mob6_retained":   bool(r["mob6_retained"]),
                    "mob12_retained":  bool(r["mob12_retained"]),
                    "channel":         r["segment"],
                    "product":         r["product"],
                    **{m: bool(r[f"pfi_{m}"]) for m in PFI_MILESTONES},
                }
            ),
            axis=1,
        )

        insert_df = full_df[["name", "segment", "criteria", "size",
                              "period_start", "period_end"]].copy()

        conn.execute("""
            INSERT INTO cohorts (id, name, segment, criteria, size, period_start, period_end)
            SELECT
                gen_random_uuid(),
                name,
                segment,
                criteria::JSON,
                size,
                period_start::DATE,
                period_end::DATE
            FROM insert_df
        """)
        conn.commit()
    finally:
        if close_conn:
            conn.close()

    return validated


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    df = seed()
    mob6_rate  = df["mob6_retained"].mean()
    mob12_rate = df["mob12_retained"].mean()
    quality_dist = df["quality_score"].value_counts(normalize=True).to_dict()
    offer_dist   = df["offer_type"].value_counts(normalize=True).to_dict()

    print(f"Seeded {len(df):,} cohort member rows into cohorts table")
    print(f"  MOB6  retention : {mob6_rate:.1%}")
    print(f"  MOB12 retention : {mob12_rate:.1%}")
    print(f"  Quality dist    : high={quality_dist.get('high', 0):.1%}, "
          f"medium={quality_dist.get('medium', 0):.1%}, "
          f"low={quality_dist.get('low', 0):.1%}")
    print(f"  Offer dist      : cash_bonus={offer_dist.get('cash_bonus', 0):.1%}, "
          f"stacked={offer_dist.get('stacked', 0):.1%}, "
          f"no_offer={offer_dist.get('no_offer', 0):.1%}")
    print("  Pandera validation: PASSED")
