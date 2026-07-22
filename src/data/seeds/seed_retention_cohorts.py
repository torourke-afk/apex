"""Seed: Retention Cohort Data

Generates ~2,592 rows: 12 months × 18 MOB × 4 channels × 3 markets.
CRITICAL shape requirements:
  - Exponential decay: MOB1≈95%, MOB3≈90%, MOB6≈80%, MOB12≈70%
  - Channel ordering: SEM > Social > Display (at every MOB)
  - Realistic active/churned account counts consistent with retention_rate

Idempotent: DELETE + INSERT on retention_cohorts.

Run:
    python -m src.data.seeds.seed_retention_cohorts
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
from src.data.seeds._dates import TWELVE_MONTH_STRINGS  # noqa: E402

SEED = 42
rng = np.random.default_rng(SEED)

# Dimensions
ACQUISITION_MONTHS = TWELVE_MONTH_STRINGS
MOBS: List[int] = list(range(0, 18))  # MOB 0–17

# Channel ordering enforced: SEM > Social > Display
CHANNELS = ["sem", "social", "display", "direct"]
# Base retention at MOB1 by channel (must be decreasing SEM→Social→Display)
CHANNEL_BASE_MOB1 = {
    "sem":     0.960,
    "social":  0.948,
    "display": 0.932,
    "direct":  0.955,
}

MARKETS = ["tier_1", "tier_2", "tier_3"]
# Market modifier: tier_1 retains best
MARKET_MODIFIER = {"tier_1": +0.015, "tier_2": 0.0, "tier_3": -0.018}

OFFER_TYPES = ["standard", "dd_incentive", "rate_match", "bundled"]
PRODUCT_MIXES = ["checking_only", "checking_savings", "full_suite"]
QUALITY_BANDS = ["high", "mid", "low"]

# Exponential decay targets anchored at MOB1 = ~95% baseline
# decay_lambda set so: exp(-lambda*11) ≈ 0.70/0.95 at MOB12
# 0.70/0.95 = 0.7368 → -lambda*11 = ln(0.7368) → lambda ≈ 0.0268
DECAY_LAMBDA = 0.0268

# Starting cohort size per (channel, market) slice
COHORT_SIZE_BASE = 2_500


def _retention_at_mob(mob: int, channel: str, market: str,
                       quality_band: str, noise_scale: float = 0.008) -> float:
    """Compute retention rate at given MOB with channel/market/quality adjustments."""
    if mob == 0:
        return 1.0

    base_mob1 = CHANNEL_BASE_MOB1[channel]
    market_adj = MARKET_MODIFIER[market]
    quality_adj = {"high": +0.012, "mid": 0.0, "low": -0.014}[quality_band]

    # Exponential decay from MOB1 base
    base = (base_mob1 + market_adj + quality_adj) * np.exp(-DECAY_LAMBDA * (mob - 1))
    noise = float(rng.normal(0, noise_scale))
    return float(np.clip(base + noise, 0.55, 0.99))


def build_retention_cohorts() -> pd.DataFrame:
    rows = []
    now = pd.Timestamp.now()

    for acq_month in ACQUISITION_MONTHS:
        for channel in CHANNELS:
            for market in MARKETS:
                # Vary offer_type/product_mix/quality_band per cohort slice
                offer_type = rng.choice(OFFER_TYPES)
                product_mix = rng.choice(PRODUCT_MIXES)
                quality_band = rng.choice(QUALITY_BANDS, p=[0.35, 0.45, 0.20])

                # Starting accounts with some variance
                size_noise = float(rng.uniform(0.85, 1.15))
                start_accounts = int(COHORT_SIZE_BASE * size_noise)

                # Track cumulative active accounts for consistency
                prev_active = start_accounts

                for mob in MOBS:
                    retention_rate = _retention_at_mob(mob, channel, market, quality_band)

                    if mob == 0:
                        active_accounts = start_accounts
                        churned_accounts = 0
                    else:
                        # Active at this MOB is retention_rate applied to initial cohort
                        active_accounts = max(1, int(start_accounts * retention_rate))
                        churned_accounts = start_accounts - active_accounts

                    # Snap retention_rate to be consistent with counts
                    total = active_accounts + churned_accounts
                    if total > 0 and mob > 0:
                        retention_rate = round(active_accounts / total, 4)
                    else:
                        retention_rate = round(retention_rate, 4)

                    rows.append({
                        "id":               str(uuid.uuid4()),
                        "acquisition_month": acq_month,
                        "channel":          channel,
                        "market":           market,
                        "offer_type":       offer_type,
                        "product_mix":      product_mix,
                        "quality_score_band": quality_band,
                        "mob":              mob,
                        "retention_rate":   retention_rate,
                        "active_accounts":  active_accounts,
                        "churned_accounts": churned_accounts,
                        "created_at":       now,
                        "updated_at":       now,
                    })

    return pd.DataFrame(rows)


COHORT_SCHEMA = DataFrameSchema(
    {
        "id":               Column(str, nullable=False),
        "acquisition_month": Column(str, nullable=False),
        "channel":          Column(str, Check.isin(CHANNELS)),
        "market":           Column(str, Check.isin(MARKETS)),
        "offer_type":       Column(str, nullable=False),
        "product_mix":      Column(str, nullable=False),
        "quality_score_band": Column(str, Check.isin(["high", "mid", "low"])),
        "mob":              Column(int, Check.in_range(0, 17)),
        "retention_rate":   Column(float, Check.in_range(0.0, 1.0)),
        "active_accounts":  Column(int, Check.greater_than_or_equal_to(0)),
        "churned_accounts": Column(int, Check.greater_than_or_equal_to(0)),
    },
    checks=[
        Check(lambda df: len(df) >= 2000, error="Expected >= 2,000 cohort rows"),
        Check(
            lambda df: (
                df[df["mob"] == 1].groupby("channel")["retention_rate"].mean()
                .reindex(["sem", "social", "display"])
                .is_monotonic_decreasing
            ),
            error="SEM > Social > Display retention ordering violated at MOB1",
        ),
        Check(
            lambda df: (
                df[df["channel"] == "sem"].groupby("mob")["retention_rate"].mean()
                .reset_index()
                .pipe(lambda x: x.loc[x["mob"].isin([1, 12])]["retention_rate"].values)
                .tolist()[0] > df[df["channel"] == "sem"].groupby("mob")["retention_rate"]
                .mean().reset_index()
                .pipe(lambda x: x.loc[x["mob"] == 12]["retention_rate"].values[0])
            ),
            error="Exponential decay not present in SEM channel",
        ),
    ],
    coerce=True,
)


def seed(verbose: bool = True) -> pd.DataFrame:
    df = build_retention_cohorts()

    for col in ("retention_rate",):
        df[col] = df[col].astype(float)
    for col in ("mob", "active_accounts", "churned_accounts"):
        df[col] = df[col].astype(int)

    COHORT_SCHEMA.validate(df)

    # Verify channel ordering in aggregate
    mob1 = df[df["mob"] == 1]
    avg_by_channel = mob1.groupby("channel")["retention_rate"].mean()
    assert avg_by_channel["sem"] > avg_by_channel["social"] > avg_by_channel["display"], \
        f"Channel ordering violated: {avg_by_channel.to_dict()}"

    conn = get_connection()
    try:
        conn.execute("DELETE FROM retention_cohorts")
        conn.register("rc_df", df)
        conn.execute("""
            INSERT INTO retention_cohorts
                (id, acquisition_month, channel, market, offer_type, product_mix,
                 quality_score_band, mob, retention_rate, active_accounts,
                 churned_accounts, created_at, updated_at)
            SELECT id, acquisition_month, channel, market, offer_type, product_mix,
                   quality_score_band, mob, retention_rate, active_accounts,
                   churned_accounts, created_at, updated_at
            FROM rc_df
        """)
        conn.commit()
    finally:
        try:
            conn.unregister("rc_df")
        except Exception:
            pass
        conn.close()

    if verbose:
        print(f"[seed_retention_cohorts] Inserted {len(df):,} rows into retention_cohorts")
        mob_anchors = df[df["mob"].isin([1, 3, 6, 12])].groupby("mob")["retention_rate"].mean()
        print("  Decay anchors (avg across all slices):")
        for mob_val, rate in mob_anchors.items():
            print(f"    MOB{mob_val:>2}: {rate:.1%}")
        print("  Channel ordering at MOB1:")
        for ch, rate in avg_by_channel.sort_values(ascending=False).items():
            print(f"    {ch:<10}: {rate:.1%}")

    return df


if __name__ == "__main__":
    seed()
