"""Seed: Social & Brand Media Data (APE-80)

Generates seed data for five tables:
  - social_platform_metrics   — 4 platforms × 12 weeks = 48 rows
  - social_creatives          — ~40 rows across platforms (~20% underperformers)
  - brand_market_bei          — 15 markets (5/tier) × 12 weeks = 180 rows
  - life_event_campaigns      — 8 event types × 12 periods = 96 rows
  - mover_marketing           — 10 geos × 12 periods = 120 rows

Meta receives ~70% of total weekly social spend.
Idempotent: DELETE + INSERT on each table.

Run:
    python -m src.data.seeds.seed_social_brand
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import date, timedelta
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
from src.data.seeds._dates import TWELVE_WEEK_MONDAYS  # noqa: E402

SEED = 42
rng = np.random.default_rng(SEED)

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

# 12 weekly periods (Mondays) from centralized date anchor
WEEKS: list[date] = [d.date() for d in TWELVE_WEEK_MONDAYS]
WEEK_STRS: list[str] = [str(w) for w in WEEKS]

PLATFORMS = ["Meta", "TikTok", "LinkedIn", "Other"]
# Meta ~70% spend share; remainder split across others
PLATFORM_SPEND_SHARE = {"Meta": 0.70, "TikTok": 0.15, "LinkedIn": 0.10, "Other": 0.05}

TOTAL_WEEKLY_SPEND = 500_000  # $500K/week total social budget


# ---------------------------------------------------------------------------
# 1. social_platform_metrics
# ---------------------------------------------------------------------------

def build_social_platform_metrics() -> pd.DataFrame:
    rows = []
    now = pd.Timestamp.now()

    # Platform-specific CPL baselines and CVR parameters
    platform_params = {
        "Meta":     {"cpl": 35,  "cvr_native": 0.055, "cvr_landing": 0.032, "cpa_ai_factor": 0.82},
        "TikTok":   {"cpl": 42,  "cvr_native": 0.038, "cvr_landing": 0.025, "cpa_ai_factor": 0.78},
        "LinkedIn": {"cpl": 110, "cvr_native": 0.028, "cvr_landing": 0.018, "cpa_ai_factor": 0.85},
        "Other":    {"cpl": 55,  "cvr_native": 0.030, "cvr_landing": 0.022, "cpa_ai_factor": 0.80},
    }

    for week_idx, week in enumerate(WEEKS):
        trend = 1 + week_idx * 0.005  # slight upward improvement over time
        for platform in PLATFORMS:
            p = platform_params[platform]
            share = PLATFORM_SPEND_SHARE[platform]
            spend = round(TOTAL_WEEKLY_SPEND * share * (1 + float(rng.normal(0, 0.03))), 2)

            cpm = float(rng.uniform(8, 18))
            impressions = int(spend / cpm * 1000)
            ctr = float(rng.uniform(0.008, 0.025))
            clicks = int(impressions * ctr)

            cvr_native = float(np.clip(p["cvr_native"] * trend + rng.normal(0, 0.003), 0.005, 0.12))
            cvr_landing = float(np.clip(p["cvr_landing"] * trend + rng.normal(0, 0.002), 0.003, 0.08))
            leads = max(1, int(clicks * cvr_native))
            cpl = round(spend / leads, 2) if leads > 0 else p["cpl"]

            cpa_manual = round(cpl / cvr_landing * 1.0, 2)
            cpa_ai = round(cpa_manual * p["cpa_ai_factor"] * (1 + float(rng.normal(0, 0.02))), 2)

            first_party = int(rng.integers(50_000, 500_000))

            rows.append({
                "id":                   str(uuid.uuid4()),
                "platform":             platform,
                "period":               str(week),
                "spend":                spend,
                "impressions":          impressions,
                "clicks":               clicks,
                "leads":                leads,
                "cpl":                  cpl,
                "cvr_native":           round(cvr_native, 6),
                "cvr_landing":          round(cvr_landing, 6),
                "cpa_ai":               cpa_ai,
                "cpa_manual":           cpa_manual,
                "first_party_audiences": first_party,
                "created_at":           now,
                "updated_at":           now,
            })

    return pd.DataFrame(rows)


SOCIAL_PLATFORM_SCHEMA = DataFrameSchema(
    {
        "id":                    Column(str, nullable=False),
        "platform":              Column(str, Check.isin(PLATFORMS)),
        "period":                Column(str, nullable=False),
        "spend":                 Column(float, Check.greater_than(0)),
        "impressions":           Column(int, Check.greater_than(0)),
        "clicks":                Column(int, Check.greater_than_or_equal_to(0)),
        "leads":                 Column(int, Check.greater_than_or_equal_to(0)),
        "cpl":                   Column(float, Check.greater_than(0)),
        "cvr_native":            Column(float, Check.in_range(0, 1)),
        "cvr_landing":           Column(float, Check.in_range(0, 1)),
        "cpa_ai":                Column(float, Check.greater_than(0)),
        "cpa_manual":            Column(float, Check.greater_than(0)),
        "first_party_audiences": Column(int, Check.greater_than(0)),
    },
    checks=[
        Check(lambda df: len(df) == 48, error="Expected 48 rows (4 platforms × 12 weeks)"),
        Check(
            lambda df: (
                df[df["platform"] == "Meta"]["spend"].sum() /
                df["spend"].sum()
            ) > 0.65,
            error="Meta spend share should be ~70%",
        ),
    ],
    coerce=True,
)


# ---------------------------------------------------------------------------
# 2. social_creatives
# ---------------------------------------------------------------------------

CREATIVE_FORMATS = ["image", "video", "carousel"]
N_CREATIVES = 40

def build_social_creatives() -> pd.DataFrame:
    rows = []
    now = pd.Timestamp.now()

    # Platform-specific CTR medians for underperformer flagging
    platform_ctr_median = {"Meta": 0.015, "TikTok": 0.018, "LinkedIn": 0.010, "Other": 0.012}

    for i in range(N_CREATIVES):
        platform = PLATFORMS[i % len(PLATFORMS)]  # distribute evenly
        fmt = str(rng.choice(CREATIVE_FORMATS))
        # ~20% are flagged underperformers (CTR below median); rest are above
        is_underperformer = bool(rng.random() < 0.20)
        median = platform_ctr_median[platform]
        if is_underperformer:
            ctr = float(np.clip(rng.uniform(0.001, median * 0.85), 0.001, median))
        else:
            ctr = float(np.clip(rng.normal(median * 1.3, 0.004), median, 0.05))
        cvr = float(np.clip(rng.normal(0.035, 0.01), 0.005, 0.10))
        spend = round(float(rng.uniform(5_000, 80_000)), 2)
        impressions = int(spend / float(rng.uniform(8, 18)) * 1000)

        rows.append({
            "id":               str(uuid.uuid4()),
            "creative_id":      f"CRV-{i+1:04d}",
            "platform":         platform,
            "name":             f"{platform} {fmt.title()} Ad #{i+1:03d}",
            "format":           fmt,
            "ctr":              round(ctr, 6),
            "cvr":              round(cvr, 6),
            "spend":            spend,
            "impressions":      impressions,
            "is_underperformer": is_underperformer,
            "created_at":       now,
            "updated_at":       now,
        })

    return pd.DataFrame(rows)


SOCIAL_CREATIVES_SCHEMA = DataFrameSchema(
    {
        "id":               Column(str, nullable=False),
        "creative_id":      Column(str, nullable=False),
        "platform":         Column(str, Check.isin(PLATFORMS)),
        "name":             Column(str, nullable=False),
        "format":           Column(str, Check.isin(CREATIVE_FORMATS)),
        "ctr":              Column(float, Check.in_range(0, 1)),
        "cvr":              Column(float, Check.in_range(0, 1)),
        "spend":            Column(float, Check.greater_than(0)),
        "impressions":      Column(int, Check.greater_than(0)),
        "is_underperformer": Column(bool),
    },
    checks=[
        Check(lambda df: len(df) == N_CREATIVES, error=f"Expected {N_CREATIVES} creative rows"),
        Check(
            lambda df: 0.10 <= df["is_underperformer"].mean() <= 0.40,
            error="Underperformer rate should be ~20% (10–40% tolerance)",
        ),
    ],
    coerce=True,
)


# ---------------------------------------------------------------------------
# 3. brand_market_bei
# ---------------------------------------------------------------------------

MARKET_TIERS = {
    "Tier1": [
        "New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX", "Phoenix, AZ"
    ],
    "Tier2": [
        "Philadelphia, PA", "San Antonio, TX", "San Diego, CA", "Dallas, TX", "San Jose, CA"
    ],
    "Tier3": [
        "Austin, TX", "Jacksonville, FL", "Fort Worth, TX", "Columbus, OH", "Charlotte, NC"
    ],
}

# Tier-based BEI score ranges
TIER_BEI_PARAMS = {
    "Tier1": {"center": 72, "noise": 6},
    "Tier2": {"center": 58, "noise": 7},
    "Tier3": {"center": 44, "noise": 8},
}

# 5 component weights for BEI (must sum to 1.0)
BEI_WEIGHTS = {
    "awareness_score":          0.25,
    "branded_search_score":     0.25,
    "direct_traffic_score":     0.20,
    "branch_visits_score":      0.20,
    "social_engagement_score":  0.10,
}


def _bei_composite(row: dict) -> float:
    return sum(row[k] * w for k, w in BEI_WEIGHTS.items())


def build_brand_market_bei() -> pd.DataFrame:
    rows = []
    now = pd.Timestamp.now()

    for tier, markets in MARKET_TIERS.items():
        params = TIER_BEI_PARAMS[tier]
        for market_idx, market in enumerate(markets):
            # Control markets: 1 per tier is control (is_active_market=False)
            is_active = market_idx < 4  # 4 active, 1 control per tier

            for week_idx, week in enumerate(WEEKS):
                trend = week_idx * 0.20  # gentle upward trend

                components = {}
                for comp in BEI_WEIGHTS:
                    raw = params["center"] + trend + float(rng.normal(0, params["noise"]))
                    components[comp] = round(float(np.clip(raw, 10, 100)), 2)

                bei = round(_bei_composite(components), 2)

                freq_compliance = round(float(np.clip(rng.normal(0.72, 0.08), 0.30, 1.0)), 4)
                ctv_comp = round(float(np.clip(rng.normal(0.68, 0.07), 0.30, 1.0)), 4)
                olv_comp = round(float(np.clip(rng.normal(0.74, 0.07), 0.30, 1.0)), 4)
                audio_ltr = round(float(np.clip(rng.normal(0.62, 0.08), 0.20, 1.0)), 4)

                lift = None
                if is_active and week_idx >= 4:
                    lift = round(float(np.clip(rng.normal(0.08, 0.04), 0.0, 0.30)), 4)

                rows.append({
                    "id":                       str(uuid.uuid4()),
                    "market_name":              market,
                    "market_tier":              tier,
                    "week_ending":              str(week),
                    **{k: v for k, v in components.items()},
                    "bei_score":                bei,
                    "frequency_compliance":     freq_compliance,
                    "ctv_completion_rate":      ctv_comp,
                    "olv_completion_rate":      olv_comp,
                    "audio_listen_through_rate": audio_ltr,
                    "is_active_market":         is_active,
                    "incrementality_lift":      lift,
                    "created_at":               now,
                    "updated_at":               now,
                })

    return pd.DataFrame(rows)


BRAND_MARKET_BEI_SCHEMA = DataFrameSchema(
    {
        "id":                        Column(str, nullable=False),
        "market_name":               Column(str, nullable=False),
        "market_tier":               Column(str, Check.isin(["Tier1", "Tier2", "Tier3"])),
        "week_ending":               Column(str, nullable=False),
        "awareness_score":           Column(float, Check.in_range(0, 100)),
        "branded_search_score":      Column(float, Check.in_range(0, 100)),
        "direct_traffic_score":      Column(float, Check.in_range(0, 100)),
        "branch_visits_score":       Column(float, Check.in_range(0, 100)),
        "social_engagement_score":   Column(float, Check.in_range(0, 100)),
        "bei_score":                 Column(float, Check.in_range(0, 100)),
        "frequency_compliance":      Column(float, Check.in_range(0, 1)),
        "ctv_completion_rate":       Column(float, Check.in_range(0, 1)),
        "olv_completion_rate":       Column(float, Check.in_range(0, 1)),
        "audio_listen_through_rate": Column(float, Check.in_range(0, 1)),
        "is_active_market":          Column(bool),
    },
    checks=[
        Check(lambda df: len(df) == 180, error="Expected 180 rows (15 markets × 12 weeks)"),
        Check(
            lambda df: (
                df[df["market_tier"] == "Tier1"]["bei_score"].mean() >
                df[df["market_tier"] == "Tier2"]["bei_score"].mean() >
                df[df["market_tier"] == "Tier3"]["bei_score"].mean()
            ),
            error="Tier1 > Tier2 > Tier3 BEI ordering violated",
        ),
    ],
    coerce=True,
)


# ---------------------------------------------------------------------------
# 4. life_event_campaigns
# ---------------------------------------------------------------------------

LIFE_EVENTS = [
    "HomePurchase", "Marriage", "NewChild", "College",
    "Inheritance", "JobChange", "Divorce", "Retirement",
]

# Event-specific CVR multipliers and segment sizes
EVENT_PARAMS = {
    "HomePurchase": {"cvr": 0.048, "mass_cvr": 0.018, "seg": 120_000},
    "Marriage":     {"cvr": 0.042, "mass_cvr": 0.016, "seg": 95_000},
    "NewChild":     {"cvr": 0.038, "mass_cvr": 0.015, "seg": 110_000},
    "College":      {"cvr": 0.035, "mass_cvr": 0.014, "seg": 85_000},
    "Inheritance":  {"cvr": 0.055, "mass_cvr": 0.020, "seg": 45_000},
    "JobChange":    {"cvr": 0.032, "mass_cvr": 0.013, "seg": 150_000},
    "Divorce":      {"cvr": 0.030, "mass_cvr": 0.012, "seg": 60_000},
    "Retirement":   {"cvr": 0.060, "mass_cvr": 0.022, "seg": 70_000},
}

SEGMENT_PARAMETER_TEMPLATES = {
    "HomePurchase": {"income_min": 75_000, "credit_score_min": 680, "data_source": "CoreLogic"},
    "Marriage":     {"age_range": [25, 45], "data_source": "Experian"},
    "NewChild":     {"age_range": [25, 40], "data_source": "Experian"},
    "College":      {"age_range": [17, 22], "data_source": "Epsilon"},
    "Inheritance":  {"asset_trigger": True, "data_source": "LexisNexis"},
    "JobChange":    {"linkedin_signal": True, "data_source": "LiveRamp"},
    "Divorce":      {"credit_event": "separation", "data_source": "Equifax"},
    "Retirement":   {"age_min": 58, "income_tier": "high", "data_source": "Acxiom"},
}


def build_life_event_campaigns() -> pd.DataFrame:
    rows = []
    now = pd.Timestamp.now()

    for week_idx, week in enumerate(WEEKS):
        trend = 1 + week_idx * 0.004
        for event in LIFE_EVENTS:
            p = EVENT_PARAMS[event]
            cvr = round(float(np.clip(p["cvr"] * trend + rng.normal(0, 0.003), 0.005, 0.15)), 6)
            mass_cvr = round(float(np.clip(p["mass_cvr"] * trend + rng.normal(0, 0.001), 0.003, 0.05)), 6)
            multiplier = round(cvr / mass_cvr, 2) if mass_cvr > 0 else 0.0
            segment_size = int(p["seg"] * (1 + float(rng.normal(0, 0.05))))
            status = "active" if week_idx < 10 else "paused"

            seg_params = dict(SEGMENT_PARAMETER_TEMPLATES[event])
            seg_params["week"] = str(week)

            rows.append({
                "id":                  str(uuid.uuid4()),
                "event_type":          event,
                "period":              str(week),
                "status":              status,
                "cvr":                 cvr,
                "mass_market_cvr":     mass_cvr,
                "cvr_multiplier":      multiplier,
                "segment_size":        segment_size,
                "segment_parameters":  json.dumps(seg_params),
                "created_at":          now,
                "updated_at":          now,
            })

    return pd.DataFrame(rows)


LIFE_EVENT_SCHEMA = DataFrameSchema(
    {
        "id":               Column(str, nullable=False),
        "event_type":       Column(str, Check.isin(LIFE_EVENTS)),
        "period":           Column(str, nullable=False),
        "status":           Column(str, Check.isin(["active", "paused"])),
        "cvr":              Column(float, Check.in_range(0, 1)),
        "mass_market_cvr":  Column(float, Check.in_range(0, 1)),
        "cvr_multiplier":   Column(float, Check.greater_than(0)),
        "segment_size":     Column(int, Check.greater_than(0)),
        "segment_parameters": Column(str, nullable=False),
    },
    checks=[
        Check(lambda df: len(df) == 96, error="Expected 96 rows (8 events × 12 weeks)"),
        Check(
            lambda df: df["cvr_multiplier"].median() >= 1.5,
            error="Median CVR multiplier should reflect life-event uplift (≥1.5×)",
        ),
    ],
    coerce=True,
)


# ---------------------------------------------------------------------------
# 5. mover_marketing
# ---------------------------------------------------------------------------

GEOS = [
    "Charlotte, NC",
    "Atlanta, GA",
    "Nashville, TN",
    "Denver, CO",
    "Austin, TX",
    "Raleigh, NC",
    "Tampa, FL",
    "Phoenix, AZ",
    "Columbus, OH",
    "Indianapolis, IN",
]

GEO_PARAMS = {
    "Charlotte, NC":   {"vol": 3_200, "quality": 72, "expansion": False},
    "Atlanta, GA":     {"vol": 4_100, "quality": 68, "expansion": False},
    "Nashville, TN":   {"vol": 2_800, "quality": 74, "expansion": True},
    "Denver, CO":      {"vol": 2_500, "quality": 70, "expansion": True},
    "Austin, TX":      {"vol": 3_800, "quality": 75, "expansion": False},
    "Raleigh, NC":     {"vol": 2_200, "quality": 71, "expansion": True},
    "Tampa, FL":       {"vol": 3_000, "quality": 67, "expansion": False},
    "Phoenix, AZ":     {"vol": 3_500, "quality": 69, "expansion": False},
    "Columbus, OH":    {"vol": 2_600, "quality": 66, "expansion": True},
    "Indianapolis, IN": {"vol": 2_100, "quality": 65, "expansion": False},
}


def build_mover_marketing() -> pd.DataFrame:
    rows = []
    now = pd.Timestamp.now()

    for week_idx, week in enumerate(WEEKS):
        trend = 1 + week_idx * 0.006
        for geo in GEOS:
            p = GEO_PARAMS[geo]
            vol = int(p["vol"] * trend * (1 + float(rng.normal(0, 0.05))))
            quality = round(float(np.clip(p["quality"] + week_idx * 0.15 + rng.normal(0, 2), 40, 100)), 2)
            cvr = round(float(np.clip(rng.normal(0.045, 0.008), 0.01, 0.15)), 6)
            propensity = round(float(np.clip(rng.normal(4.0, 0.5), 2.5, 7.0)), 2)
            hi_cvr = round(float(np.clip(cvr * 1.4 + rng.normal(0, 0.005), 0.01, 0.25)), 6)
            hi_vol = int(vol * float(rng.uniform(0.18, 0.28)))

            rows.append({
                "id":                       str(uuid.uuid4()),
                "geo":                      geo,
                "period":                   str(week),
                "pipeline_volume":          vol,
                "pipeline_quality_score":   quality,
                "mover_to_account_cvr":     cvr,
                "propensity_benchmark":     propensity,
                "is_expansion_geo":         p["expansion"],
                "high_income_subset_cvr":   hi_cvr,
                "high_income_subset_volume": hi_vol,
                "created_at":               now,
                "updated_at":               now,
            })

    return pd.DataFrame(rows)


MOVER_MARKETING_SCHEMA = DataFrameSchema(
    {
        "id":                        Column(str, nullable=False),
        "geo":                       Column(str, nullable=False),
        "period":                    Column(str, nullable=False),
        "pipeline_volume":           Column(int, Check.greater_than(0)),
        "pipeline_quality_score":    Column(float, Check.in_range(0, 100)),
        "mover_to_account_cvr":      Column(float, Check.in_range(0, 1)),
        "propensity_benchmark":      Column(float, Check.greater_than(0)),
        "is_expansion_geo":          Column(bool),
        "high_income_subset_cvr":    Column(float, Check.in_range(0, 1)),
        "high_income_subset_volume": Column(int, Check.greater_than_or_equal_to(0)),
    },
    checks=[
        Check(lambda df: len(df) == 120, error="Expected 120 rows (10 geos × 12 weeks)"),
        Check(
            lambda df: df["propensity_benchmark"].mean() >= 3.0,
            error="Avg propensity benchmark should reflect 3–5× target",
        ),
    ],
    coerce=True,
)


# ---------------------------------------------------------------------------
# DB seed helpers
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


def seed(verbose: bool = True) -> dict[str, pd.DataFrame]:
    dfs: dict[str, pd.DataFrame] = {}
    conn = get_connection()
    try:
        # --- social_platform_metrics ---
        df = build_social_platform_metrics()
        for col in ("spend", "cpl", "cvr_native", "cvr_landing", "cpa_ai", "cpa_manual"):
            df[col] = df[col].astype(float)
        SOCIAL_PLATFORM_SCHEMA.validate(df)
        _insert(conn, "social_platform_metrics", df, [
            "id", "platform", "period", "spend", "impressions", "clicks",
            "leads", "cpl", "cvr_native", "cvr_landing", "cpa_ai", "cpa_manual",
            "first_party_audiences", "created_at", "updated_at",
        ])
        dfs["social_platform_metrics"] = df
        if verbose:
            print(f"[seed_social_brand] social_platform_metrics: {len(df)} rows")
            meta_share = df[df["platform"] == "Meta"]["spend"].sum() / df["spend"].sum()
            print(f"  Meta spend share: {meta_share:.1%}")

        # --- social_creatives ---
        df = build_social_creatives()
        for col in ("ctr", "cvr", "spend"):
            df[col] = df[col].astype(float)
        SOCIAL_CREATIVES_SCHEMA.validate(df)
        _insert(conn, "social_creatives", df, [
            "id", "creative_id", "platform", "name", "format",
            "ctr", "cvr", "spend", "impressions", "is_underperformer",
            "created_at", "updated_at",
        ])
        dfs["social_creatives"] = df
        if verbose:
            underperf_pct = df["is_underperformer"].mean()
            print(f"[seed_social_brand] social_creatives: {len(df)} rows ({underperf_pct:.0%} underperformers)")

        # --- brand_market_bei ---
        df = build_brand_market_bei()
        for col in ("awareness_score", "branded_search_score", "direct_traffic_score",
                    "branch_visits_score", "social_engagement_score", "bei_score",
                    "frequency_compliance", "ctv_completion_rate",
                    "olv_completion_rate", "audio_listen_through_rate"):
            df[col] = df[col].astype(float)
        BRAND_MARKET_BEI_SCHEMA.validate(df)
        _insert(conn, "brand_market_bei", df, [
            "id", "market_name", "market_tier", "week_ending",
            "awareness_score", "branded_search_score", "direct_traffic_score",
            "branch_visits_score", "social_engagement_score", "bei_score",
            "frequency_compliance", "ctv_completion_rate", "olv_completion_rate",
            "audio_listen_through_rate", "is_active_market", "incrementality_lift",
            "created_at", "updated_at",
        ])
        dfs["brand_market_bei"] = df
        if verbose:
            for tier in ["Tier1", "Tier2", "Tier3"]:
                avg = df[df["market_tier"] == tier]["bei_score"].mean()
                print(f"  {tier} avg BEI: {avg:.1f}")
            print(f"[seed_social_brand] brand_market_bei: {len(df)} rows")

        # --- life_event_campaigns ---
        df = build_life_event_campaigns()
        for col in ("cvr", "mass_market_cvr", "cvr_multiplier"):
            df[col] = df[col].astype(float)
        LIFE_EVENT_SCHEMA.validate(df)
        _insert(conn, "life_event_campaigns", df, [
            "id", "event_type", "period", "status", "cvr", "mass_market_cvr",
            "cvr_multiplier", "segment_size", "segment_parameters",
            "created_at", "updated_at",
        ])
        dfs["life_event_campaigns"] = df
        if verbose:
            mult = df["cvr_multiplier"].median()
            print(f"[seed_social_brand] life_event_campaigns: {len(df)} rows (median CVR mult: {mult:.2f}×)")

        # --- mover_marketing ---
        df = build_mover_marketing()
        for col in ("pipeline_quality_score", "mover_to_account_cvr",
                    "propensity_benchmark", "high_income_subset_cvr"):
            df[col] = df[col].astype(float)
        MOVER_MARKETING_SCHEMA.validate(df)
        _insert(conn, "mover_marketing", df, [
            "id", "geo", "period", "pipeline_volume", "pipeline_quality_score",
            "mover_to_account_cvr", "propensity_benchmark", "is_expansion_geo",
            "high_income_subset_cvr", "high_income_subset_volume",
            "created_at", "updated_at",
        ])
        dfs["mover_marketing"] = df
        if verbose:
            print(f"[seed_social_brand] mover_marketing: {len(df)} rows")

        conn.commit()

    finally:
        conn.close()

    return dfs


if __name__ == "__main__":
    results = seed(verbose=True)
    total = sum(len(v) for v in results.values())
    print(f"\nTotal rows seeded: {total}")
