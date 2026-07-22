"""Seed: PFI Milestone Completion Rates

Generates 72 rows: 12 acquisition cohorts × 6 milestone types.
Rates cluster around targets with realistic variance.

Idempotent: DELETE + INSERT on pfi_milestones.

Run:
    python -m src.data.seeds.seed_pfi_milestones
"""

from __future__ import annotations

import os
import sys
import uuid
from decimal import Decimal

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

# 12 acquisition cohorts (months)
COHORTS = TWELVE_MONTH_STRINGS

# Milestone definitions: type → (target_pct, target_days, tracking_source, switching_cost)
MILESTONES = {
    "direct_deposit":  (0.72, 45,  "payroll_provider",    "high"),
    "bill_pay":        (0.58, 60,  "digital_banking_log", "medium"),
    "debit_card":      (0.85, 14,  "card_activation_api", "low"),
    "digital_wallet":  (0.48, 30,  "digital_banking_log", "low"),
    "p2p_payments":    (0.35, 90,  "payments_platform",   "medium"),
    "cross_sell":      (0.22, 120, "crm_platform",        "high"),
}

# Slight upward trend across cohorts (newer cohorts perform a touch better)
TREND_GAIN_PER_COHORT = 0.003


def build_pfi_milestones() -> pd.DataFrame:
    rows = []
    now = pd.Timestamp.now()

    for cohort_idx, cohort in enumerate(COHORTS):
        trend = cohort_idx * TREND_GAIN_PER_COHORT
        for milestone_type, (target_pct, target_days, source, switching_cost) in MILESTONES.items():
            # Actual rate = target + trend + noise (±8% std dev, clipped to [5%, 98%])
            noise = float(rng.normal(0, 0.045))
            actual_pct = float(np.clip(target_pct + trend + noise, 0.05, 0.98))
            rows.append({
                "id":             str(uuid.uuid4()),
                "milestone_type": milestone_type,
                "target_pct":     round(target_pct, 4),
                "actual_pct":     round(actual_pct, 4),
                "target_days":    target_days,
                "tracking_source": source,
                "switching_cost": switching_cost,
                "cohort_month":   cohort,
                "created_at":     now,
                "updated_at":     now,
            })

    return pd.DataFrame(rows)


PFI_SCHEMA = DataFrameSchema(
    {
        "id":             Column(str, nullable=False),
        "milestone_type": Column(str, Check.isin(list(MILESTONES.keys()))),
        "target_pct":     Column(float, Check.in_range(0.0, 1.0)),
        "actual_pct":     Column(float, Check.in_range(0.0, 1.0)),
        "target_days":    Column(int, Check.greater_than(0)),
        "tracking_source": Column(str, nullable=False),
        "switching_cost": Column(str, Check.isin(["low", "medium", "high"])),
        "cohort_month":   Column(str, nullable=False),
    },
    checks=[
        Check(lambda df: len(df) == 72, error="Expected exactly 72 rows (12 cohorts × 6 milestones)"),
        Check(lambda df: df["milestone_type"].nunique() == 6, error="Expected 6 milestone types"),
    ],
    coerce=True,
)

_DDL = """
CREATE TABLE IF NOT EXISTS pfi_milestones (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    milestone_type  VARCHAR NOT NULL,
    target_pct      DECIMAL(6, 4) NOT NULL,
    actual_pct      DECIMAL(6, 4) NOT NULL,
    target_days     INTEGER NOT NULL,
    tracking_source VARCHAR NOT NULL,
    switching_cost  VARCHAR NOT NULL,
    cohort_month    VARCHAR(7),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP
)
"""


def seed(verbose: bool = True) -> pd.DataFrame:
    df = build_pfi_milestones()

    df["target_pct"] = df["target_pct"].astype(float)
    df["actual_pct"] = df["actual_pct"].astype(float)

    PFI_SCHEMA.validate(df)

    conn = get_connection()
    try:
        # Ensure cohort_month column exists (migration-safe)
        existing_cols = {
            row[0].lower()
            for row in conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'pfi_milestones'"
            ).fetchall()
        }
        if "cohort_month" not in existing_cols:
            conn.execute("ALTER TABLE pfi_milestones ADD COLUMN cohort_month VARCHAR(7)")
            if verbose:
                print("[seed_pfi_milestones] Migration: added cohort_month column")

        conn.execute("DELETE FROM pfi_milestones")
        conn.register("pfi_df", df)
        conn.execute("""
            INSERT INTO pfi_milestones
                (id, milestone_type, target_pct, actual_pct, target_days,
                 tracking_source, switching_cost, cohort_month, created_at, updated_at)
            SELECT id, milestone_type, target_pct, actual_pct, target_days,
                   tracking_source, switching_cost, cohort_month, created_at, updated_at
            FROM pfi_df
        """)
        conn.commit()
    finally:
        try:
            conn.unregister("pfi_df")
        except Exception:
            pass
        conn.close()

    if verbose:
        print(f"[seed_pfi_milestones] Inserted {len(df)} rows into pfi_milestones")
        for mtype, grp in df.groupby("milestone_type"):
            print(f"  {mtype:<20} target={grp['target_pct'].mean():.2%}  "
                  f"actual={grp['actual_pct'].mean():.2%}  "
                  f"(±{grp['actual_pct'].std():.2%} std)")

    return df


if __name__ == "__main__":
    seed()
