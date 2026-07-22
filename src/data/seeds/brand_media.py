"""Seed: Brand Media Data (APE-99)

Generates seed data for three tables:
  - brand_media_bei_weekly          — 15 markets × 12 weeks = 180 rows
  - brand_media_performance         — 15 markets × 12 weeks = 180 rows
  - brand_media_incrementality_pairs — 6 market pairs with lift measurement

Brand media spend = 40% of $15,000,000 total media budget = $6,000,000 annual.

Market tiers:
  - Growth (5 markets):     BEI trending up     (55–75 range)
  - Maintain (5 markets):   BEI stable          (65–80 range)
  - Experiment (5 markets): BEI volatile        (45–70 range)

BEI components weighted sum:
  awareness (0.35) + consideration (0.30) + preference (0.25) + advocacy (0.10)

Idempotent: DELETE + INSERT on each table.

Run:
    python -m src.data.seeds.brand_media
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema, Check

WORKSPACE = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if WORKSPACE not in sys.path:
    sys.path.insert(0, WORKSPACE)

from src.data.init_db import get_connection, init_db  # noqa: E402
from src.data.seeds._dates import TWELVE_WEEK_MONDAYS  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SEED = 42
rng = np.random.default_rng(SEED)

TOTAL_MEDIA_BUDGET = 15_000_000.0
BRAND_MEDIA_BUDGET = TOTAL_MEDIA_BUDGET * 0.40  # $6,000,000

# 12 weekly periods (Mondays) from centralized date anchor
WEEKS: list[date] = [d.date() for d in TWELVE_WEEK_MONDAYS]

# Market definitions by tier
GROWTH_MARKETS = [
    "Charlotte, NC",
    "Nashville, TN",
    "Austin, TX",
    "Raleigh, NC",
    "Denver, CO",
]
MAINTAIN_MARKETS = [
    "Cincinnati, OH",
    "Columbus, OH",
    "Indianapolis, IN",
    "Louisville, KY",
    "Lexington, KY",
]
EXPERIMENT_MARKETS = [
    "Tampa, FL",
    "Orlando, FL",
    "Jacksonville, FL",
    "Atlanta, GA",
    "Memphis, TN",
]

MARKET_TIER_MAP: dict[str, str] = (
    {m: "Growth" for m in GROWTH_MARKETS}
    | {m: "Maintain" for m in MAINTAIN_MARKETS}
    | {m: "Experiment" for m in EXPERIMENT_MARKETS}
)
ALL_MARKETS = GROWTH_MARKETS + MAINTAIN_MARKETS + EXPERIMENT_MARKETS

# BEI component weights — must sum to 1.0
BEI_WEIGHTS = {
    "awareness_score":     0.35,
    "consideration_score": 0.30,
    "preference_score":    0.25,
    "advocacy_score":      0.10,
}

# Per-tier BEI generation params: (start_center, end_center, noise_std)
# Growth: trending up from ~58 to ~72 over 12 weeks
# Maintain: stable around 72 (low noise)
# Experiment: volatile, no trend (high noise, center ~57)
TIER_BEI_PARAMS = {
    "Growth":     {"start": 58.0, "end": 72.0, "noise": 3.0},
    "Maintain":   {"start": 72.0, "end": 73.0, "noise": 2.0},
    "Experiment": {"start": 57.0, "end": 57.0, "noise": 9.0},
}

# Tier-based spend weights (must sum to 1.0 across 5 markets each)
TIER_SPEND_WEIGHT = {"Growth": 0.45, "Maintain": 0.35, "Experiment": 0.20}


# ---------------------------------------------------------------------------
# 1. brand_media_bei_weekly
# ---------------------------------------------------------------------------

def _bei_composite(components: dict[str, float]) -> float:
    return sum(components[k] * w for k, w in BEI_WEIGHTS.items())


def build_bei_weekly() -> pd.DataFrame:
    rows = []
    now = pd.Timestamp.now()

    for market in ALL_MARKETS:
        tier = MARKET_TIER_MAP[market]
        params = TIER_BEI_PARAMS[tier]

        for week_idx, week in enumerate(WEEKS):
            # Linear interpolation between start and end centers
            t = week_idx / (len(WEEKS) - 1)
            center = params["start"] + t * (params["end"] - params["start"])
            noise_std = params["noise"]

            components: dict[str, float] = {}
            for comp in BEI_WEIGHTS:
                raw = center + float(rng.normal(0, noise_std))
                components[comp] = round(float(np.clip(raw, 10.0, 100.0)), 2)

            bei = round(_bei_composite(components), 2)

            rows.append({
                "id":                  str(uuid.uuid4()),
                "market_name":         market,
                "market_tier":         tier,
                "week_ending":         str(week),
                "awareness_score":     components["awareness_score"],
                "consideration_score": components["consideration_score"],
                "preference_score":    components["preference_score"],
                "advocacy_score":      components["advocacy_score"],
                "bei_score":           bei,
                "created_at":          now,
                "updated_at":          now,
            })

    return pd.DataFrame(rows)


BEI_WEEKLY_SCHEMA = DataFrameSchema(
    {
        "id":                  Column(str, nullable=False),
        "market_name":         Column(str, nullable=False),
        "market_tier":         Column(str, Check.isin(["Growth", "Maintain", "Experiment"])),
        "week_ending":         Column(str, nullable=False),
        "awareness_score":     Column(float, Check.in_range(10, 100)),
        "consideration_score": Column(float, Check.in_range(10, 100)),
        "preference_score":    Column(float, Check.in_range(10, 100)),
        "advocacy_score":      Column(float, Check.in_range(10, 100)),
        "bei_score":           Column(float, Check.in_range(10, 100)),
    },
    checks=[
        Check(lambda df: len(df) == 180, error="Expected 180 rows (15 markets × 12 weeks)"),
        # Growth BEI should be in 55-75 range on average
        Check(
            lambda df: df[df["market_tier"] == "Growth"]["bei_score"].between(45, 85).all(),
            error="Growth BEI scores outside expected band",
        ),
        # Maintain BEI should be in 65-80 range
        Check(
            lambda df: df[df["market_tier"] == "Maintain"]["bei_score"].between(55, 90).all(),
            error="Maintain BEI scores outside expected band",
        ),
        # Growth markets must show upward trend (last 4 weeks avg > first 4 weeks avg)
        Check(
            lambda df: (
                df[df["market_tier"] == "Growth"]
                .sort_values("week_ending")
                .groupby("market_name")["bei_score"]
                .apply(lambda s: s.iloc[-4:].mean() > s.iloc[:4].mean())
                .mean()
            ) >= 0.6,
            error="Growth markets must trend upward (≥60% of markets)",
        ),
    ],
    coerce=True,
)


# ---------------------------------------------------------------------------
# 2. brand_media_performance
# ---------------------------------------------------------------------------

# CTV/OLV completion rate params by creative length
CTV_OLV_PARAMS = {
    "ctv_15s_completion":  {"center": 0.925, "noise": 0.018},  # 85-95%, 15s highest
    "ctv_30s_completion":  {"center": 0.895, "noise": 0.020},  # 85-93%
    "olv_15s_completion":  {"center": 0.910, "noise": 0.018},  # 85-95%
    "olv_30s_completion":  {"center": 0.878, "noise": 0.020},  # 85-93%
}

# Audio listen-through: 70-85%
AUDIO_PARAMS = {"center": 0.775, "noise": 0.035}

# Frequency compliance by tier: Growth highest (80-95%), Maintain (70-85%), Experiment (60-75%)
FREQ_COMPLIANCE_PARAMS = {
    "Growth":     {"center": 0.875, "noise": 0.035},
    "Maintain":   {"center": 0.775, "noise": 0.035},
    "Experiment": {"center": 0.675, "noise": 0.035},
}


def build_media_performance() -> pd.DataFrame:
    """Build media performance rows. Spend is allocated by tier weight and scaled
    to exactly equal BRAND_MEDIA_BUDGET ($6M)."""
    rows = []
    now = pd.Timestamp.now()

    # Pre-compute raw spend weights for exact reconciliation
    raw_spends: list[float] = []
    for market in ALL_MARKETS:
        tier = MARKET_TIER_MAP[market]
        base_weight = TIER_SPEND_WEIGHT[tier] / len(GROWTH_MARKETS)  # each tier has 5 markets
        for _ in WEEKS:
            noise = 1.0 + float(rng.normal(0, 0.08))
            raw_spends.append(base_weight * noise)

    total_raw = sum(raw_spends)
    scale = BRAND_MEDIA_BUDGET / total_raw

    spend_iter = iter([s * scale for s in raw_spends])

    for market in ALL_MARKETS:
        tier = MARKET_TIER_MAP[market]
        freq_p = FREQ_COMPLIANCE_PARAMS[tier]

        for week in WEEKS:
            spend = round(next(spend_iter), 2)
            # CPM $12-18 range typical for brand media
            cpm = float(rng.uniform(12.0, 18.0))
            impressions = max(1, int(spend / cpm * 1000))

            # Completion rates
            completions: dict[str, float] = {}
            for col, p in CTV_OLV_PARAMS.items():
                raw = p["center"] + float(rng.normal(0, p["noise"]))
                completions[col] = round(float(np.clip(raw, 0.80, 0.98)), 4)

            audio_ltr = round(float(np.clip(
                AUDIO_PARAMS["center"] + rng.normal(0, AUDIO_PARAMS["noise"]),
                0.65, 0.90
            )), 4)

            freq_compliance = round(float(np.clip(
                freq_p["center"] + rng.normal(0, freq_p["noise"]),
                0.55, 0.98
            )), 4)

            rows.append({
                "id":                   str(uuid.uuid4()),
                "market_name":          market,
                "market_tier":          tier,
                "week_ending":          str(week),
                "spend":                spend,
                "impressions":          impressions,
                "ctv_15s_completion":   completions["ctv_15s_completion"],
                "ctv_30s_completion":   completions["ctv_30s_completion"],
                "olv_15s_completion":   completions["olv_15s_completion"],
                "olv_30s_completion":   completions["olv_30s_completion"],
                "audio_listen_through": audio_ltr,
                "frequency_compliance": freq_compliance,
                "created_at":           now,
                "updated_at":           now,
            })

    return pd.DataFrame(rows)


MEDIA_PERFORMANCE_SCHEMA = DataFrameSchema(
    {
        "id":                   Column(str, nullable=False),
        "market_name":          Column(str, nullable=False),
        "market_tier":          Column(str, Check.isin(["Growth", "Maintain", "Experiment"])),
        "week_ending":          Column(str, nullable=False),
        "spend":                Column(float, Check.greater_than(0)),
        "impressions":          Column(int, Check.greater_than(0)),
        "ctv_15s_completion":   Column(float, Check.in_range(0.75, 1.0)),
        "ctv_30s_completion":   Column(float, Check.in_range(0.75, 1.0)),
        "olv_15s_completion":   Column(float, Check.in_range(0.75, 1.0)),
        "olv_30s_completion":   Column(float, Check.in_range(0.75, 1.0)),
        "audio_listen_through": Column(float, Check.in_range(0.60, 0.95)),
        "frequency_compliance": Column(float, Check.in_range(0.50, 1.0)),
    },
    checks=[
        Check(lambda df: len(df) == 180, error="Expected 180 rows (15 markets × 12 weeks)"),
        # 15s completion rates > 30s completion rates (on average)
        Check(
            lambda df: df["ctv_15s_completion"].mean() > df["ctv_30s_completion"].mean(),
            error="CTV 15s completion must average higher than 30s",
        ),
        Check(
            lambda df: df["olv_15s_completion"].mean() > df["olv_30s_completion"].mean(),
            error="OLV 15s completion must average higher than 30s",
        ),
        # Budget reconciliation: total spend = 40% of $15M = $6M (±$10 tolerance)
        Check(
            lambda df: abs(df["spend"].sum() - BRAND_MEDIA_BUDGET) < 10.0,
            error=f"Total brand media spend must equal ${BRAND_MEDIA_BUDGET:,.0f} (±$10)",
        ),
        # Growth markets should have higher frequency compliance
        Check(
            lambda df: (
                df[df["market_tier"] == "Growth"]["frequency_compliance"].mean() >
                df[df["market_tier"] == "Experiment"]["frequency_compliance"].mean()
            ),
            error="Growth markets must average higher frequency compliance than Experiment",
        ),
        # Audio listen-through: 70-85% on average
        Check(
            lambda df: 0.68 <= df["audio_listen_through"].mean() <= 0.88,
            error="Audio listen-through average should be in 70-85% range",
        ),
    ],
    coerce=True,
)


# ---------------------------------------------------------------------------
# 3. brand_media_incrementality_pairs
# ---------------------------------------------------------------------------

# 6 active/control market pairs
# 4 statistically significant (p < 0.05), 2 not significant
_PAIRS_DEF = [
    # (pair_name, active_market, control_market, is_significant)
    ("Growth-Charlotte vs Maintain-Cincinnati",   "Charlotte, NC",    "Cincinnati, OH",    True),
    ("Growth-Nashville vs Maintain-Columbus",      "Nashville, TN",    "Columbus, OH",      True),
    ("Growth-Austin vs Experiment-Tampa",          "Austin, TX",       "Tampa, FL",         True),
    ("Growth-Raleigh vs Maintain-Indianapolis",    "Raleigh, NC",      "Indianapolis, IN",  True),
    ("Maintain-Louisville vs Experiment-Orlando",  "Louisville, KY",   "Orlando, FL",       False),
    ("Maintain-Lexington vs Experiment-Atlanta",   "Lexington, KY",    "Atlanta, GA",       False),
]

_TEST_START = WEEKS[0]
_TEST_END = WEEKS[-1]


def build_incrementality_pairs() -> pd.DataFrame:
    rows = []
    now = pd.Timestamp.now()

    for pair_name, active, control, is_sig in _PAIRS_DEF:
        if is_sig:
            # Statistically significant: lift 8-20%, p < 0.05, confidence > 0.92
            observed_lift = round(float(rng.uniform(0.08, 0.20)), 4)
            p_value = round(float(rng.uniform(0.008, 0.048)), 6)
            confidence_level = round(float(np.clip(1.0 - p_value * 2.5, 0.92, 0.99)), 4)
            sample_size = int(rng.integers(18_000, 45_000))
        else:
            # Not significant: lift 1-5%, p > 0.10
            observed_lift = round(float(rng.uniform(0.01, 0.05)), 4)
            p_value = round(float(rng.uniform(0.12, 0.45)), 6)
            confidence_level = round(float(np.clip(1.0 - p_value, 0.55, 0.88)), 4)
            sample_size = int(rng.integers(8_000, 18_000))

        rows.append({
            "id":                 str(uuid.uuid4()),
            "pair_name":          pair_name,
            "active_market":      active,
            "control_market":     control,
            "test_start_date":    str(_TEST_START),
            "test_end_date":      str(_TEST_END),
            "observed_lift":      observed_lift,
            "confidence_level":   confidence_level,
            "p_value":            p_value,
            "is_significant":     is_sig,
            "sample_size":        sample_size,
            "created_at":         now,
            "updated_at":         now,
        })

    return pd.DataFrame(rows)


INCREMENTALITY_PAIRS_SCHEMA = DataFrameSchema(
    {
        "id":               Column(str, nullable=False),
        "pair_name":        Column(str, nullable=False),
        "active_market":    Column(str, nullable=False),
        "control_market":   Column(str, nullable=False),
        "test_start_date":  Column(str, nullable=False),
        "test_end_date":    Column(str, nullable=False),
        "observed_lift":    Column(float, Check.in_range(0.0, 0.50)),
        "confidence_level": Column(float, Check.in_range(0.0, 1.0)),
        "p_value":          Column(float, Check.in_range(0.0, 1.0)),
        "is_significant":   Column(bool),
        "sample_size":      Column(int, Check.greater_than(0)),
    },
    checks=[
        Check(
            lambda df: df["pair_name"].nunique() >= 5,
            error="Must have 5–8 incrementality pairs",
        ),
        Check(
            lambda df: df["pair_name"].nunique() <= 8,
            error="Must have 5–8 incrementality pairs",
        ),
        Check(
            lambda df: df["is_significant"].sum() >= 3,
            error="Must have 3–5 statistically significant pairs",
        ),
        Check(
            lambda df: df["is_significant"].sum() <= 5,
            error="Must have 3–5 statistically significant pairs",
        ),
        # Significant pairs should have lower p-values
        Check(
            lambda df: (
                df[df["is_significant"]]["p_value"].max() < 0.05
            ),
            error="All significant pairs must have p_value < 0.05",
        ),
        # Non-significant pairs should have higher p-values
        Check(
            lambda df: (
                df[~df["is_significant"]]["p_value"].min() > 0.05
            ),
            error="Non-significant pairs must have p_value > 0.05",
        ),
        # Significant lifts should exceed non-significant
        Check(
            lambda df: (
                df[df["is_significant"]]["observed_lift"].mean() >
                df[~df["is_significant"]]["observed_lift"].mean()
            ),
            error="Significant pairs must show higher average lift",
        ),
    ],
    coerce=True,
)


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _insert(conn, table: str, df: pd.DataFrame, columns: list[str]) -> None:
    conn.execute(f"DELETE FROM {table}")
    conn.register(f"_df_{table}", df)
    cols = ", ".join(columns)
    conn.execute(f"INSERT INTO {table} ({cols}) SELECT {cols} FROM _df_{table}")
    try:
        conn.unregister(f"_df_{table}")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_brand_media_data(
    verbose: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Generate and seed all brand media tables.

    Returns:
        (bei_weekly, media_performance, incrementality_pairs) DataFrames.
    """
    init_db()  # ensure brand media tables exist
    conn = get_connection()
    try:
        # --- brand_media_bei_weekly ---
        bei_weekly = build_bei_weekly()
        for col in ("awareness_score", "consideration_score", "preference_score",
                    "advocacy_score", "bei_score"):
            bei_weekly[col] = bei_weekly[col].astype(float)
        BEI_WEEKLY_SCHEMA.validate(bei_weekly)
        _insert(conn, "brand_media_bei_weekly", bei_weekly, [
            "id", "market_name", "market_tier", "week_ending",
            "awareness_score", "consideration_score", "preference_score",
            "advocacy_score", "bei_score", "created_at", "updated_at",
        ])
        if verbose:
            print(f"[brand_media] brand_media_bei_weekly: {len(bei_weekly)} rows")
            for tier in ["Growth", "Maintain", "Experiment"]:
                grp = bei_weekly[bei_weekly["market_tier"] == tier]
                print(f"  {tier}: BEI {grp['bei_score'].min():.1f}–"
                      f"{grp['bei_score'].max():.1f} "
                      f"(avg {grp['bei_score'].mean():.1f})")

        # --- brand_media_performance ---
        media_performance = build_media_performance()
        for col in ("spend", "ctv_15s_completion", "ctv_30s_completion",
                    "olv_15s_completion", "olv_30s_completion",
                    "audio_listen_through", "frequency_compliance"):
            media_performance[col] = media_performance[col].astype(float)
        MEDIA_PERFORMANCE_SCHEMA.validate(media_performance)
        _insert(conn, "brand_media_performance", media_performance, [
            "id", "market_name", "market_tier", "week_ending", "spend", "impressions",
            "ctv_15s_completion", "ctv_30s_completion",
            "olv_15s_completion", "olv_30s_completion",
            "audio_listen_through", "frequency_compliance",
            "created_at", "updated_at",
        ])
        if verbose:
            total_spend = media_performance["spend"].sum()
            print(f"[brand_media] brand_media_performance: {len(media_performance)} rows "
                  f"(total spend ${total_spend:,.0f} = "
                  f"{total_spend / TOTAL_MEDIA_BUDGET:.0%} of media budget)")
            print(f"  CTV 15s avg completion: {media_performance['ctv_15s_completion'].mean():.1%}")
            print(f"  CTV 30s avg completion: {media_performance['ctv_30s_completion'].mean():.1%}")
            print(f"  Audio listen-through avg: {media_performance['audio_listen_through'].mean():.1%}")

        # --- brand_media_incrementality_pairs ---
        incrementality_pairs = build_incrementality_pairs()
        for col in ("observed_lift", "confidence_level", "p_value"):
            incrementality_pairs[col] = incrementality_pairs[col].astype(float)
        INCREMENTALITY_PAIRS_SCHEMA.validate(incrementality_pairs)
        _insert(conn, "brand_media_incrementality_pairs", incrementality_pairs, [
            "id", "pair_name", "active_market", "control_market",
            "test_start_date", "test_end_date",
            "observed_lift", "confidence_level", "p_value",
            "is_significant", "sample_size",
            "created_at", "updated_at",
        ])
        if verbose:
            sig = incrementality_pairs["is_significant"].sum()
            total = len(incrementality_pairs)
            print(f"[brand_media] brand_media_incrementality_pairs: {total} pairs "
                  f"({sig} significant)")
            for _, row in incrementality_pairs.iterrows():
                sig_flag = "✓ sig" if row["is_significant"] else "  n.s."
                print(f"  {sig_flag}  {row['pair_name']}: "
                      f"lift={row['observed_lift']:.1%}, p={row['p_value']:.3f}")

        conn.commit()

    finally:
        conn.close()

    return bei_weekly, media_performance, incrementality_pairs


# Alias expected by run_all.py
def seed(verbose: bool = True) -> pd.DataFrame:
    """Seed all brand media tables; return bei_weekly for row-count reporting."""
    bei_weekly, media_performance, incrementality_pairs = generate_brand_media_data(
        verbose=verbose
    )
    total = len(bei_weekly) + len(media_performance) + len(incrementality_pairs)
    return pd.DataFrame({"_count": [total]})  # run_all uses len(df) for row count


if __name__ == "__main__":
    bei, perf, pairs = generate_brand_media_data(verbose=True)
    total = len(bei) + len(perf) + len(pairs)
    print(f"\nTotal rows seeded: {total}")
