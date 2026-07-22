"""Seed Acquisition Funnel module data (APE-56).

Generates five funnel tables:

  1. funnel_events            — 6-stage waterfall, 90 days, ~100k daily top-of-funnel
                                segmented by channel × market_tier × persona_segment
                                (product_type + device sampled per cell as metadata)
  2. funnel_benchmarks        — static industry avg + top-performer rates per stage transition
  3. funnel_abandonment_recovery — 5 Kamino re-engagement windows per stage/channel/day
  4. funnel_landing_pages     — page variants with conversion lever metrics
  5. funnel_personalization   — persona segment A/B test velocity tracker

Waterfall arithmetic: each stage count = binomial(prev_count, effective_rate)
guaranteeing volume_in × conversion_rate ≈ volume_out.

Idempotent: truncates all five funnel tables before re-inserting.
"""

from __future__ import annotations

import sys
import os
import uuid
from datetime import date, timedelta
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import pandera as pa
from pandera import Column, DataFrameSchema, Check
import duckdb

from src.data.seeds._dates import TRAILING_90D_START, TRAILING_90D_END

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
WORKSPACE = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, WORKSPACE)
from src.config.settings import DB_PATH  # noqa: E402

# ---------------------------------------------------------------------------
# RNG
# ---------------------------------------------------------------------------
SEED = 42
rng = np.random.default_rng(SEED)

# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------

# 7 funnel nodes, 6 transitions
STAGES: List[str] = [
    "page_visit",
    "app_start",
    "form_complete",
    "kyc_pass",
    "approval",
    "funded",
    "active_90d",
]

CHANNELS: List[str] = [
    "Paid Search",
    "Paid Social",
    "Organic Search",
    "Direct Mail",
    "Email",
    "Display",
    "Referral",
]

MARKET_TIERS: List[str] = ["Tier 1", "Tier 2", "Tier 3"]

PRODUCT_TYPES: List[str] = [
    "Checking Account",
    "Savings Account",
    "Personal Loan",
    "Auto Loan",
    "Mortgage",
    "Credit Card",
    "Home Equity",
]

DEVICES: List[str] = ["desktop", "mobile", "tablet"]

PERSONA_SEGMENTS: List[str] = [
    "High-intent Saver",
    "Rate Shopper",
    "Life Event",
    "Re-engager",
    "Mass Market",
]

# ---------------------------------------------------------------------------
# Date range — trailing 90 days ending yesterday
# ---------------------------------------------------------------------------
START_DATE = TRAILING_90D_START
END_DATE = TRAILING_90D_END
DATES: List[date] = [START_DATE + timedelta(days=i) for i in range(90)]

# ---------------------------------------------------------------------------
# Conversion rate spec (industry avg, top performer)
# key = destination stage
# ---------------------------------------------------------------------------
# (industry_avg, top_performer) — used for benchmarks table
# Rates aligned to spec §2: PV→AS 55%/65%, remaining per industry benchmarks
CONV_BENCHMARKS: Dict[str, Tuple[float, float]] = {
    "app_start":     (0.55, 0.65),   # page_visit → app_start
    "form_complete": (0.66, 0.80),   # app_start  → form_complete
    "kyc_pass":      (0.80, 0.91),   # form_complete → kyc_pass
    "approval":      (0.87, 0.95),   # kyc_pass → approval
    "funded":        (0.76, 0.90),   # approval → funded
    "active_90d":    (0.73, 0.89),   # funded → active_90d
}

# Base rates for simulation (midpoint of top-performer range)
BASE_CONV: Dict[str, float] = {
    k: (v[0] + v[1]) / 2 for k, v in CONV_BENCHMARKS.items()
}

# ---------------------------------------------------------------------------
# Channel × tier × persona multipliers
# ---------------------------------------------------------------------------

CHANNEL_CONV_MULT: Dict[str, Dict[str, float]] = {
    "Paid Search": {
        "app_start": 1.10, "form_complete": 1.08, "kyc_pass": 1.05,
        "approval": 1.03, "funded": 1.05, "active_90d": 1.04,
    },
    "Paid Social": {
        "app_start": 0.95, "form_complete": 0.97, "kyc_pass": 0.98,
        "approval": 0.98, "funded": 0.96, "active_90d": 0.95,
    },
    "Organic Search": {
        "app_start": 1.08, "form_complete": 1.10, "kyc_pass": 1.07,
        "approval": 1.05, "funded": 1.06, "active_90d": 1.08,
    },
    "Direct Mail": {
        "app_start": 1.00, "form_complete": 1.05, "kyc_pass": 1.03,
        "approval": 1.04, "funded": 1.07, "active_90d": 1.05,
    },
    "Email": {
        "app_start": 1.12, "form_complete": 1.06, "kyc_pass": 1.04,
        "approval": 1.03, "funded": 1.08, "active_90d": 1.06,
    },
    "Display": {
        "app_start": 0.82, "form_complete": 0.87, "kyc_pass": 0.91,
        "approval": 0.93, "funded": 0.88, "active_90d": 0.87,
    },
    "Referral": {
        "app_start": 1.18, "form_complete": 1.14, "kyc_pass": 1.12,
        "approval": 1.10, "funded": 1.14, "active_90d": 1.18,
    },
}

TIER_CONV_MOD: Dict[str, float] = {
    "Tier 1": 1.06,
    "Tier 2": 1.00,
    "Tier 3": 0.91,
}

# Persona conversion multipliers (applied uniformly across all transitions)
PERSONA_CONV_MULT: Dict[str, float] = {
    "High-intent Saver": 1.20,
    "Rate Shopper":      1.08,
    "Life Event":        1.28,
    "Re-engager":        0.85,
    "Mass Market":       1.00,
}

# ---------------------------------------------------------------------------
# Daily page-visit volumes per channel (scaled for ~100k total/day)
# 105 cells/day (7 ch × 3 tier × 5 persona) × ~952 avg = ~100k
# ---------------------------------------------------------------------------
CHANNEL_DAILY_VISITS: Dict[str, Tuple[int, int]] = {
    "Paid Search":    (800,  1600),   # avg ~1200
    "Paid Social":    (1000, 2000),   # avg ~1500
    "Organic Search": (600,  1000),   # avg ~800
    "Direct Mail":    (250,   600),   # avg ~425
    "Email":          (400,   900),   # avg ~650
    "Display":        (1400, 2500),   # avg ~1950
    "Referral":       (250,   600),   # avg ~425
}
# Grand avg ≈ 993 → 105 cells × 993 ≈ 104k/day (close to target)

# Device sampling weights (for metadata only; doesn't affect volume)
DEVICE_WEIGHTS = [0.35, 0.50, 0.15]

# ---------------------------------------------------------------------------
# Seasonality
# ---------------------------------------------------------------------------

def _dow_factor(d: date) -> float:
    dow = d.weekday()
    return 1.0 + 0.03 * (4 - abs(dow - 2)) if dow < 5 else 0.72


def _monthly_factor(d: date) -> float:
    return {
        1: 1.20, 2: 1.10, 3: 1.18, 4: 1.12, 5: 1.05,
        6: 0.95, 7: 0.88, 8: 0.92, 9: 1.05, 10: 1.15,
        11: 1.10, 12: 0.90,
    }[d.month]


def _season(d: date) -> float:
    return _dow_factor(d) * _monthly_factor(d)


# ---------------------------------------------------------------------------
# 1. funnel_events — waterfall cohort rows
# ---------------------------------------------------------------------------

def _build_funnel_events() -> pd.DataFrame:
    """Generate funnel_events: one row per (date, channel, tier, persona, stage)."""
    n_cells = len(DATES) * len(CHANNELS) * len(MARKET_TIERS) * len(PERSONA_SEGMENTS)
    # Sample product_type and device as metadata per cell
    sampled_products = rng.choice(PRODUCT_TYPES, size=n_cells).tolist()
    sampled_devices = rng.choice(DEVICES, size=n_cells, p=DEVICE_WEIGHTS).tolist()

    all_rows: List[dict] = []
    cell_idx = 0

    for d in DATES:
        season = _season(d)
        for channel in CHANNELS:
            lo, hi = CHANNEL_DAILY_VISITS[channel]
            for tier in MARKET_TIERS:
                tier_mult = TIER_CONV_MOD[tier]
                for persona in PERSONA_SEGMENTS:
                    product = sampled_products[cell_idx]
                    device = sampled_devices[cell_idx]
                    cell_idx += 1

                    # Top-of-funnel: page_visits
                    base_visits = int(rng.integers(lo, hi + 1) * season)
                    base_visits = max(base_visits, 1)

                    persona_mult = PERSONA_CONV_MULT[persona]
                    count = base_visits

                    for i, stage in enumerate(STAGES):
                        all_rows.append({
                            "id":                   str(uuid.uuid4()),
                            "stage":                stage,
                            "event_date":           d.isoformat(),
                            "channel":              channel,
                            "market_tier":          tier,
                            "product_type":         product,
                            "device":               device,
                            "personalization_segment": persona,
                            "count":                count,
                        })

                        if i == len(STAGES) - 1:
                            break

                        next_stage = STAGES[i + 1]
                        base_rate = BASE_CONV[next_stage]
                        ch_mult = CHANNEL_CONV_MULT[channel][next_stage]
                        jitter = float(rng.uniform(-0.015, 0.015))
                        effective_rate = float(np.clip(
                            base_rate * ch_mult * tier_mult * persona_mult + jitter,
                            0.05, 0.99,
                        ))
                        count = int(rng.binomial(count, effective_rate)) if count > 0 else 0

    df = pd.DataFrame(all_rows)
    df["count"] = df["count"].astype(int)
    return df


FUNNEL_EVENTS_SCHEMA = DataFrameSchema(
    {
        "id":                      Column(str, Check(lambda s: s.str.len() == 36)),
        "stage":                   Column(str, Check.isin(STAGES)),
        "event_date":              Column(str, nullable=False),
        "channel":                 Column(str, Check.isin(CHANNELS)),
        "market_tier":             Column(str, Check.isin(MARKET_TIERS)),
        "product_type":            Column(str, Check.isin(PRODUCT_TYPES)),
        "device":                  Column(str, Check.isin(DEVICES)),
        "personalization_segment": Column(str, Check.isin(PERSONA_SEGMENTS)),
        "count":                   Column(int, Check(lambda s: s >= 0)),
    },
    coerce=True,
)


def _validate_monotone(df: pd.DataFrame) -> None:
    """Assert stage counts are monotonically non-increasing within each cohort."""
    errors: List[str] = []
    group_cols = ["event_date", "channel", "market_tier", "personalization_segment"]
    for name, grp in df.groupby(group_cols):
        ordered = grp.set_index("stage").reindex(STAGES)["count"].dropna().astype(int)
        for j in range(1, len(ordered)):
            if ordered.iloc[j] > ordered.iloc[j - 1]:
                errors.append(
                    f"{name}: {ordered.index[j]} ({ordered.iloc[j]}) > "
                    f"{ordered.index[j-1]} ({ordered.iloc[j-1]})"
                )
    if errors:
        raise ValueError(
            f"Monotone check failed for {len(errors)} group(s):\n"
            + "\n".join(errors[:10])
        )


# ---------------------------------------------------------------------------
# 2. funnel_benchmarks — industry avg + top performer per stage × product
# ---------------------------------------------------------------------------

STAGE_FROM_TO = [
    ("page_visit",    "app_start"),
    ("app_start",     "form_complete"),
    ("form_complete", "kyc_pass"),
    ("kyc_pass",      "approval"),
    ("approval",      "funded"),
    ("funded",        "active_90d"),
]

def _build_benchmarks() -> pd.DataFrame:
    rows: List[dict] = []
    for stage_from, stage_to in STAGE_FROM_TO:
        ind_avg, top_perf = CONV_BENCHMARKS[stage_to]
        for product in PRODUCT_TYPES:
            # Product-level offsets — mortgages and home equity have tighter funnels
            product_offset = {
                "Mortgage":         -0.06,
                "Home Equity":      -0.04,
                "Auto Loan":        -0.02,
                "Personal Loan":     0.00,
                "Credit Card":       0.02,
                "Checking Account":  0.03,
                "Savings Account":   0.02,
            }.get(product, 0.0)

            rows.append({
                "id":                  str(uuid.uuid4()),
                "stage_from":          stage_from,
                "stage_to":            stage_to,
                "product_type":        product,
                "industry_avg_rate":   round(float(np.clip(ind_avg + product_offset, 0.05, 0.99)), 4),
                "top_performer_rate":  round(float(np.clip(top_perf + product_offset, 0.05, 0.99)), 4),
            })
    return pd.DataFrame(rows)


BENCHMARKS_SCHEMA = DataFrameSchema(
    {
        "id":                  Column(str, nullable=False),
        "stage_from":          Column(str, Check.isin([s for s, _ in STAGE_FROM_TO])),
        "stage_to":            Column(str, Check.isin([t for _, t in STAGE_FROM_TO])),
        "product_type":        Column(str, Check.isin(PRODUCT_TYPES)),
        "industry_avg_rate":   Column(float, Check.in_range(0.0, 1.0)),
        "top_performer_rate":  Column(float, Check.in_range(0.0, 1.0)),
    },
    checks=[
        Check(lambda df: len(df) == 42, error="benchmarks: must have 42 rows (6 transitions × 7 products)"),
        Check(
            lambda df: (df["top_performer_rate"] > df["industry_avg_rate"]).all(),
            error="benchmarks: top_performer_rate must exceed industry_avg_rate",
        ),
    ],
    coerce=True,
)


# ---------------------------------------------------------------------------
# 3. funnel_abandonment_recovery — 5 Kamino windows
# ---------------------------------------------------------------------------

# Kamino re-engagement windows as spec §3: range labels + window-specific (not cumulative) rates
KAMINO_WINDOWS: List[str] = ["0-2h", "2-24h", "24-48h", "48-72h", "7-14d"]

# Stages at which abandonment occurs (all except active_90d)
ABANDONMENT_STAGES: List[str] = [
    "app_start",
    "form_complete",
    "kyc_pass",
    "approval",
    "funded",
]

# Base abandonment rates by stage (fraction of entrants who abandon)
STAGE_ABANDON_BASE: Dict[str, float] = {
    "app_start":     0.55,   # majority abandon after landing
    "form_complete": 0.30,
    "kyc_pass":      0.18,
    "approval":      0.12,
    "funded":        0.10,
}

# Window-specific (not cumulative) recovery rate midpoints per spec §3
# Spec ranges: 0-2h: 12-18%, 2-24h: 6-10%, 24-48h: 4-8%, 48-72h: 2-5%, 7-14d: 1-3%
WINDOW_RECOVERY_BASE: Dict[str, Tuple[float, float]] = {
    "0-2h":   (0.12, 0.18),
    "2-24h":  (0.06, 0.10),
    "24-48h": (0.04, 0.08),
    "48-72h": (0.02, 0.05),
    "7-14d":  (0.01, 0.03),
}


def _build_abandonment_recovery(funnel_events: pd.DataFrame) -> pd.DataFrame:
    """Generate abandonment recovery rows per (date, stage_abandoned, channel, window)."""
    # Pivot funnel_events to get daily channel-level page_visit counts
    pv = (
        funnel_events[funnel_events["stage"] == "page_visit"]
        .groupby(["event_date", "channel"])["count"]
        .sum()
        .reset_index()
        .rename(columns={"count": "daily_visitors"})
    )

    rows: List[dict] = []
    for _, pv_row in pv.iterrows():
        ev_date = pv_row["event_date"]
        channel = pv_row["channel"]
        daily = int(pv_row["daily_visitors"])

        for stage in ABANDONMENT_STAGES:
            abandon_base = STAGE_ABANDON_BASE[stage]
            # Rough abandonment count: daily visitors flowing into this stage
            # Approximate by applying cumulative conversion to get to this stage
            cum_conv = 1.0
            for s in STAGES[1:STAGES.index(stage) + 1]:
                cum_conv *= BASE_CONV[s]
            stage_volume = int(daily * cum_conv)
            abandoned_count = max(int(stage_volume * abandon_base), 0)

            if abandoned_count == 0:
                continue

            for window in KAMINO_WINDOWS:
                lo, hi = WINDOW_RECOVERY_BASE[window]
                # Window-specific rate drawn from spec range with jitter
                recovery_rate = float(np.clip(
                    float(rng.uniform(lo, hi)) + float(rng.uniform(-0.01, 0.01)),
                    0.005, 0.25,
                ))
                recovered_count = int(abandoned_count * recovery_rate)

                rows.append({
                    "id":              str(uuid.uuid4()),
                    "event_date":      ev_date,
                    "stage_abandoned": stage,
                    "channel":         channel,
                    "abandoned_count": abandoned_count,
                    "recovery_window": window,
                    "recovered_count": recovered_count,
                    "recovery_rate":   round(recovery_rate, 4),
                })

    return pd.DataFrame(rows)


ABANDONMENT_SCHEMA = DataFrameSchema(
    {
        "id":              Column(str, nullable=False),
        "event_date":      Column(str, nullable=False),
        "stage_abandoned": Column(str, Check.isin(ABANDONMENT_STAGES)),
        "channel":         Column(str, Check.isin(CHANNELS)),
        "abandoned_count": Column(int, Check(lambda s: s >= 0)),
        "recovery_window": Column(str, Check.isin(KAMINO_WINDOWS)),
        "recovered_count": Column(int, Check(lambda s: s >= 0)),
        "recovery_rate":   Column(float, Check.in_range(0.0, 1.0)),
    },
    checks=[
        Check(lambda df: len(df) >= 10_000, error="abandonment_recovery: must have >= 10,000 rows"),
        Check(
            lambda df: (df["recovered_count"] <= df["abandoned_count"]).all(),
            error="abandonment_recovery: recovered_count must not exceed abandoned_count",
        ),
    ],
    coerce=True,
)


# ---------------------------------------------------------------------------
# 4. funnel_landing_pages — variants with conversion lever metrics
# ---------------------------------------------------------------------------

# 12 variants per spec §4 (control + 11)
PAGE_VARIANTS: List[str] = [
    "control",
    "variant_a", "variant_b", "variant_c", "variant_d",
    "variant_e", "variant_f", "variant_g", "variant_h",
    "variant_i", "variant_j", "variant_k",
]
HERO_VARIANTS: List[str] = [
    "product_feature", "social_proof", "rate_highlight", "lifestyle",
    "testimonial", "urgency", "comparison", "benefit_led",
]
OFFER_TYPES: List[str] = ["none", "bonus_apy", "waived_fee", "cashback_signup", "rate_match"]

# Conversion delta vs baseline per variant
VARIANT_CONV_DELTA: Dict[str, float] = {
    "control":   0.000,
    "variant_a": 0.020,   # +2pp
    "variant_b": 0.048,   # +4.8pp
    "variant_c": -0.010,  # -1pp (loser)
    "variant_d": 0.031,
    "variant_e": 0.015,
    "variant_f": 0.062,   # best performer
    "variant_g": -0.005,
    "variant_h": 0.025,
    "variant_i": 0.038,
    "variant_j": 0.012,
    "variant_k": -0.018,  # clear loser
}

BASELINE_LP_CONV = 0.112   # 11.2% baseline page → app_start on landing page

# Spec §4 conversion lever baselines
_LP_PERSONALIZED_CTA_LIFT_BASE = 0.035   # +3.5pp from personalized CTA
_LP_FORM_REDUCTION_LIFT_BASE   = 0.055   # +5.5pp from form field reduction
_LP_AI_PERSONALIZATION_LIFT_BASE = 0.028  # +2.8pp from AI personalization
_LP_TRUST_SIGNAL_BASE_COUNT    = 4       # median trust signals shown

# Variants that have underperformed consistently (conv_rate < baseline - 0.005)
_LP_UNDERPERFORMERS = {"variant_c", "variant_g", "variant_k"}


def _build_landing_pages() -> pd.DataFrame:
    rows: List[dict] = []

    # Cycle hero variants and offer types across the 12 page variants
    hero_cycle = HERO_VARIANTS * 2  # 16 entries, slice to 12
    offer_cycle = ["none", "bonus_apy", "waived_fee", "cashback_signup", "rate_match",
                   "bonus_apy", "waived_fee", "none", "cashback_signup", "rate_match",
                   "none", "bonus_apy"]

    variant_hero: Dict[str, str] = {v: hero_cycle[i % len(HERO_VARIANTS)] for i, v in enumerate(PAGE_VARIANTS)}
    variant_offer: Dict[str, str] = {v: offer_cycle[i] for i, v in enumerate(PAGE_VARIANTS)}

    for d in DATES:
        season = _season(d)
        for product in PRODUCT_TYPES:
            for variant in PAGE_VARIANTS:
                base_visits = int(rng.integers(3000, 8000) * season)
                conv_rate = float(np.clip(
                    BASELINE_LP_CONV + VARIANT_CONV_DELTA[variant] + float(rng.uniform(-0.008, 0.008)),
                    0.01, 0.60,
                ))
                conversions = int(base_visits * conv_rate)
                cta_clicks = int(base_visits * float(np.clip(conv_rate * 2.1 + rng.uniform(-0.05, 0.05), 0.05, 0.95)))
                form_starts = int(base_visits * float(np.clip(conv_rate * 1.55 + rng.uniform(-0.04, 0.04), 0.05, 0.90)))
                load_time_ms = int(rng.integers(820, 2600))

                # Spec §4 conversion lever fields
                personalized_cta_lift = round(float(np.clip(
                    _LP_PERSONALIZED_CTA_LIFT_BASE + float(rng.uniform(-0.010, 0.010)), 0.0, 0.20
                )), 4)
                form_field_reduction_lift = round(float(np.clip(
                    _LP_FORM_REDUCTION_LIFT_BASE + float(rng.uniform(-0.015, 0.015)), 0.0, 0.20
                )), 4)
                ai_personalization_lift = round(float(np.clip(
                    _LP_AI_PERSONALIZATION_LIFT_BASE + float(rng.uniform(-0.008, 0.008)), 0.0, 0.15
                )), 4)
                trust_signal_count = int(rng.integers(
                    max(1, _LP_TRUST_SIGNAL_BASE_COUNT - 2),
                    _LP_TRUST_SIGNAL_BASE_COUNT + 3,
                ))
                is_underperformer = variant in _LP_UNDERPERFORMERS

                rows.append({
                    "id":                       str(uuid.uuid4()),
                    "event_date":               d.isoformat(),
                    "product_type":             product,
                    "page_variant":             variant,
                    "hero_variant":             variant_hero[variant],
                    "offer_shown":              variant_offer[variant],
                    "visits":                   base_visits,
                    "cta_clicks":               cta_clicks,
                    "form_starts":              form_starts,
                    "conversions":              conversions,
                    "conversion_rate":          round(conv_rate, 4),
                    "load_time_ms":             load_time_ms,
                    "personalized_cta_lift":    personalized_cta_lift,
                    "form_field_reduction_lift": form_field_reduction_lift,
                    "ai_personalization_lift":  ai_personalization_lift,
                    "trust_signal_count":       trust_signal_count,
                    "is_underperformer":        is_underperformer,
                })

    return pd.DataFrame(rows)


LANDING_PAGES_SCHEMA = DataFrameSchema(
    {
        "id":                        Column(str, nullable=False),
        "event_date":                Column(str, nullable=False),
        "product_type":              Column(str, Check.isin(PRODUCT_TYPES)),
        "page_variant":              Column(str, Check.isin(PAGE_VARIANTS)),
        "hero_variant":              Column(str, Check.isin(HERO_VARIANTS)),
        "offer_shown":               Column(str, Check.isin(OFFER_TYPES)),
        "visits":                    Column(int, Check(lambda s: s >= 0)),
        "cta_clicks":                Column(int, Check(lambda s: s >= 0)),
        "form_starts":               Column(int, Check(lambda s: s >= 0)),
        "conversions":               Column(int, Check(lambda s: s >= 0)),
        "conversion_rate":           Column(float, Check.in_range(0.0, 1.0)),
        "load_time_ms":              Column(int, Check(lambda s: s >= 0)),
        "personalized_cta_lift":     Column(float, Check.in_range(0.0, 1.0)),
        "form_field_reduction_lift": Column(float, Check.in_range(0.0, 1.0)),
        "ai_personalization_lift":   Column(float, Check.in_range(0.0, 1.0)),
        "trust_signal_count":        Column(int, Check(lambda s: s >= 0)),
        "is_underperformer":         Column(bool),
    },
    checks=[
        Check(lambda df: len(df) >= 2_000, error="landing_pages: must have >= 2,000 rows"),
        Check(
            lambda df: (df["conversions"] <= df["visits"]).all(),
            error="landing_pages: conversions must not exceed visits",
        ),
        Check(
            lambda df: df["page_variant"].nunique() == 12,
            error="landing_pages: must have 12 distinct page variants",
        ),
    ],
    coerce=True,
)


# ---------------------------------------------------------------------------
# 5. funnel_personalization — persona segments + A/B test velocity
# ---------------------------------------------------------------------------

AB_TESTS: List[str] = [
    "headline_copy_v2",
    "cta_button_color",
    "trust_badge_placement",
    "rate_display_format",
    "form_step_reduction",
]
AB_VARIANTS: List[str] = ["control", "treatment"]

# Baseline conversion by persona
PERSONA_BASELINE_CONV: Dict[str, float] = {
    "High-intent Saver": 0.182,
    "Rate Shopper":      0.145,
    "Life Event":        0.210,
    "Re-engager":        0.085,
    "Mass Market":       0.112,
}

# Per-test lift for treatment variant
TEST_LIFT: Dict[str, float] = {
    "headline_copy_v2":       0.035,
    "cta_button_color":       0.012,
    "trust_badge_placement":  0.028,
    "rate_display_format":    0.019,
    "form_step_reduction":    0.062,
}

# Test start offsets (days from START_DATE) so tests ramp mid-period
TEST_START_OFFSET: Dict[str, int] = {
    "headline_copy_v2":       0,
    "cta_button_color":       15,
    "trust_badge_placement":  5,
    "rate_display_format":    30,
    "form_step_reduction":    45,
}


# Audience size (total addressable in persona pool) per segment
PERSONA_AUDIENCE_SIZE: Dict[str, int] = {
    "High-intent Saver": 85_000,
    "Rate Shopper":      120_000,
    "Life Event":        45_000,
    "Re-engager":        60_000,
    "Mass Market":       250_000,
}

# Default (Mass Market) conversion rate — used for cvr_vs_default_pct
_DEFAULT_CVR = PERSONA_BASELINE_CONV["Mass Market"]

# Baseline cadence: expected tests launched per month per persona
PERSONA_BASELINE_CADENCE: Dict[str, int] = {
    "High-intent Saver": 3,
    "Rate Shopper":      2,
    "Life Event":        2,
    "Re-engager":        2,
    "Mass Market":       4,
}


def _build_personalization() -> pd.DataFrame:
    rows: List[dict] = []

    for d in DATES:
        day_idx = (d - START_DATE).days
        for persona in PERSONA_SEGMENTS:
            base_conv = PERSONA_BASELINE_CONV[persona]
            audience_size = PERSONA_AUDIENCE_SIZE[persona]
            cvr_vs_default_pct = round((base_conv / _DEFAULT_CVR - 1) * 100, 2)
            baseline_cadence = PERSONA_BASELINE_CADENCE[persona]

            # Aggregate test counts for this persona up to this date
            tests_launched_last_30d = sum(
                1 for t in AB_TESTS
                if 0 <= (day_idx - TEST_START_OFFSET[t]) < 30
            )
            tests_concluded = sum(
                1 for t in AB_TESTS
                if (day_idx - TEST_START_OFFSET[t]) > 60
            )
            # Alert if tests launched in last 30 days is below expected monthly cadence
            cadence_alert = tests_launched_last_30d < baseline_cadence

            for test in AB_TESTS:
                # Test must have started before this day
                if day_idx < TEST_START_OFFSET[test]:
                    continue
                active_days = day_idx - TEST_START_OFFSET[test] + 1

                for variant in AB_VARIANTS:
                    # Impressions grow as test accumulates exposure
                    daily_impr = int(rng.integers(800, 2500))
                    impressions = daily_impr * min(active_days, 30)  # cap at 30-day window

                    if variant == "control":
                        conv_rate = float(np.clip(
                            base_conv + float(rng.uniform(-0.008, 0.008)), 0.01, 0.60
                        ))
                        lift_pct = 0.0
                    else:
                        lift = TEST_LIFT[test]
                        conv_rate = float(np.clip(
                            base_conv + lift + float(rng.uniform(-0.008, 0.008)), 0.01, 0.60
                        ))
                        lift_pct = round((conv_rate / base_conv - 1) * 100, 2)

                    conversions = int(impressions * conv_rate)
                    # Statistical confidence increases with sample size
                    confidence_pct = float(np.clip(
                        50 + (impressions / 1000) * 5 + float(rng.uniform(-3, 3)), 50, 99
                    ))

                    # Determine test status
                    if active_days < 7:
                        status = "running"
                    elif confidence_pct >= 95 and variant == "treatment":
                        status = "significant"
                    elif active_days > 60:
                        status = "concluded"
                    else:
                        status = "running"

                    rows.append({
                        "id":                     str(uuid.uuid4()),
                        "event_date":             d.isoformat(),
                        "persona_segment":        persona,
                        "test_name":              test,
                        "variant":                variant,
                        "impressions":            impressions,
                        "conversions":            conversions,
                        "conversion_rate":        round(conv_rate, 4),
                        "lift_pct":               lift_pct,
                        "confidence_pct":         round(confidence_pct, 2),
                        "test_status":            status,
                        # Aggregate fields per spec §5
                        "audience_size":          audience_size,
                        "cvr_vs_default_pct":     cvr_vs_default_pct,
                        "tests_launched_last_30d": tests_launched_last_30d,
                        "tests_concluded":        tests_concluded,
                        "baseline_cadence":       baseline_cadence,
                        "cadence_alert":          cadence_alert,
                    })

    return pd.DataFrame(rows)


PERSONALIZATION_SCHEMA = DataFrameSchema(
    {
        "id":                      Column(str, nullable=False),
        "event_date":              Column(str, nullable=False),
        "persona_segment":         Column(str, Check.isin(PERSONA_SEGMENTS)),
        "test_name":               Column(str, Check.isin(AB_TESTS)),
        "variant":                 Column(str, Check.isin(AB_VARIANTS)),
        "impressions":             Column(int, Check(lambda s: s >= 0)),
        "conversions":             Column(int, Check(lambda s: s >= 0)),
        "conversion_rate":         Column(float, Check.in_range(0.0, 1.0)),
        "lift_pct":                Column(float),
        "confidence_pct":          Column(float, Check.in_range(0, 100)),
        "test_status":             Column(str, Check.isin(["running", "significant", "concluded"])),
        "audience_size":           Column(int, Check(lambda s: s > 0)),
        "cvr_vs_default_pct":      Column(float),
        "tests_launched_last_30d": Column(int, Check(lambda s: s >= 0)),
        "tests_concluded":         Column(int, Check(lambda s: s >= 0)),
        "baseline_cadence":        Column(int, Check(lambda s: s > 0)),
        "cadence_alert":           Column(bool),
    },
    checks=[
        Check(lambda df: len(df) >= 3_000, error="personalization: must have >= 3,000 rows"),
        Check(
            lambda df: (df["conversions"] <= df["impressions"]).all(),
            error="personalization: conversions must not exceed impressions",
        ),
    ],
    coerce=True,
)


# ---------------------------------------------------------------------------
# DDL for funnel-specific tables (created inline; not in init_db core schema)
# ---------------------------------------------------------------------------

_FUNNEL_DDL = [
    """
    CREATE TABLE IF NOT EXISTS funnel_benchmarks (
        id                  VARCHAR PRIMARY KEY,
        stage_from          VARCHAR NOT NULL,
        stage_to            VARCHAR NOT NULL,
        product_type        VARCHAR,
        industry_avg_rate   DOUBLE,
        top_performer_rate  DOUBLE,
        created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS funnel_abandonment_recovery (
        id               VARCHAR PRIMARY KEY,
        event_date       DATE NOT NULL,
        stage_abandoned  VARCHAR NOT NULL,
        channel          VARCHAR,
        abandoned_count  INTEGER DEFAULT 0,
        recovery_window  VARCHAR,
        recovered_count  INTEGER DEFAULT 0,
        recovery_rate    DOUBLE,
        created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS funnel_landing_pages (
        id                         VARCHAR PRIMARY KEY,
        event_date                 DATE NOT NULL,
        product_type               VARCHAR,
        page_variant               VARCHAR,
        hero_variant               VARCHAR,
        offer_shown                VARCHAR,
        visits                     INTEGER DEFAULT 0,
        cta_clicks                 INTEGER DEFAULT 0,
        form_starts                INTEGER DEFAULT 0,
        conversions                INTEGER DEFAULT 0,
        conversion_rate            DOUBLE,
        load_time_ms               INTEGER,
        personalized_cta_lift      DOUBLE,
        form_field_reduction_lift  DOUBLE,
        ai_personalization_lift    DOUBLE,
        trust_signal_count         INTEGER DEFAULT 0,
        is_underperformer          BOOLEAN DEFAULT FALSE,
        created_at                 TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS funnel_personalization (
        id                       VARCHAR PRIMARY KEY,
        event_date               DATE NOT NULL,
        persona_segment          VARCHAR,
        test_name                VARCHAR,
        variant                  VARCHAR,
        impressions              INTEGER DEFAULT 0,
        conversions              INTEGER DEFAULT 0,
        conversion_rate          DOUBLE,
        lift_pct                 DOUBLE,
        confidence_pct           DOUBLE,
        test_status              VARCHAR,
        audience_size            INTEGER DEFAULT 0,
        cvr_vs_default_pct       DOUBLE,
        tests_launched_last_30d  INTEGER DEFAULT 0,
        tests_concluded          INTEGER DEFAULT 0,
        baseline_cadence         INTEGER DEFAULT 0,
        cadence_alert            BOOLEAN DEFAULT FALSE,
        created_at               TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
]


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _ensure_funnel_events_columns(conn: duckdb.DuckDBPyConnection) -> None:
    """Add any missing columns to funnel_events (idempotent)."""
    existing = {
        row[0]
        for row in conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='funnel_events'"
        ).fetchall()
    }
    needed = {
        "channel":                 "VARCHAR",
        "market_tier":             "VARCHAR",
        "product_type":            "VARCHAR",
        "device":                  "VARCHAR",
        "personalization_segment": "VARCHAR",
    }
    for col, dtype in needed.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE funnel_events ADD COLUMN {col} VARCHAR")
            print(f"  Added column funnel_events.{col}")


def _insert_df(conn: duckdb.DuckDBPyConnection, df: pd.DataFrame, table: str) -> None:
    conn.register("_tmp_insert", df)
    cols = ", ".join(df.columns)
    conn.execute(f"INSERT INTO {table} ({cols}) SELECT {cols} FROM _tmp_insert")
    conn.unregister("_tmp_insert")


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def run(db_path: str = DB_PATH) -> pd.DataFrame:
    """Generate and insert all funnel seed data. Returns funnel_events DataFrame."""
    conn = duckdb.connect(db_path)

    # Bootstrap core tables
    from src.data.init_db import init_db
    init_db()

    # Recreate funnel-specific tables (drops stale schemas)
    for tbl in [
        "funnel_benchmarks",
        "funnel_abandonment_recovery",
        "funnel_landing_pages",
        "funnel_personalization",
    ]:
        conn.execute(f"DROP TABLE IF EXISTS {tbl}")
    for ddl in _FUNNEL_DDL:
        conn.execute(ddl)

    # Ensure funnel_events has all required columns
    _ensure_funnel_events_columns(conn)

    print("\n--- Building funnel_events ---")
    fe_df = _build_funnel_events()
    fe_df["count"] = fe_df["count"].astype(int)

    total_rows = len(fe_df)
    daily_pv = (
        fe_df[fe_df["stage"] == "page_visit"]
        .groupby("event_date")["count"]
        .sum()
    )
    print(f"  Rows generated:        {total_rows:,}")
    print(f"  Days covered:          {fe_df['event_date'].nunique()}")
    print(f"  Avg daily page visits: {daily_pv.mean():,.0f}  (target ~100k)")
    print(f"  Stage totals:")
    print(fe_df.groupby("stage")["count"].sum().reindex(STAGES).to_string())

    print("\n  Running Pandera validation on funnel_events...")
    FUNNEL_EVENTS_SCHEMA.validate(fe_df)
    print("  Schema validation passed.")

    print("\n  Running monotone-counts validation...")
    _validate_monotone(fe_df)
    print("  Monotone validation passed.")

    print("\n--- Building funnel_benchmarks ---")
    bm_df = _build_benchmarks()
    print(f"  Rows: {len(bm_df):,}")
    BENCHMARKS_SCHEMA.validate(bm_df)
    print("  Benchmarks schema validation passed.")

    print("\n--- Building funnel_abandonment_recovery ---")
    ab_df = _build_abandonment_recovery(fe_df)
    print(f"  Rows: {len(ab_df):,}")
    ABANDONMENT_SCHEMA.validate(ab_df)
    print("  Abandonment schema validation passed.")

    print("\n--- Building funnel_landing_pages ---")
    lp_df = _build_landing_pages()
    print(f"  Rows: {len(lp_df):,}")
    LANDING_PAGES_SCHEMA.validate(lp_df)
    print("  Landing pages schema validation passed.")

    print("\n--- Building funnel_personalization ---")
    ps_df = _build_personalization()
    print(f"  Rows: {len(ps_df):,}")
    PERSONALIZATION_SCHEMA.validate(ps_df)
    print("  Personalization schema validation passed.")

    # ----------------------------------------------------------------
    # Idempotent truncate + insert all five tables
    # ----------------------------------------------------------------
    print("\n--- Writing to DB (idempotent) ---")

    deleted = conn.execute("DELETE FROM funnel_events").rowcount
    print(f"  Deleted {deleted:,} existing funnel_events rows.")

    insert_cols = [
        "id", "stage", "event_date", "channel", "market_tier",
        "product_type", "device", "personalization_segment", "count",
    ]
    _insert_df(conn, fe_df[insert_cols].copy(), "funnel_events")
    db_fe = conn.execute("SELECT COUNT(*) FROM funnel_events").fetchone()[0]
    print(f"  funnel_events: {db_fe:,} rows written.")

    conn.execute("DELETE FROM funnel_benchmarks")
    _insert_df(conn, bm_df, "funnel_benchmarks")
    db_bm = conn.execute("SELECT COUNT(*) FROM funnel_benchmarks").fetchone()[0]
    print(f"  funnel_benchmarks: {db_bm:,} rows written.")

    conn.execute("DELETE FROM funnel_abandonment_recovery")
    _insert_df(conn, ab_df, "funnel_abandonment_recovery")
    db_ab = conn.execute("SELECT COUNT(*) FROM funnel_abandonment_recovery").fetchone()[0]
    print(f"  funnel_abandonment_recovery: {db_ab:,} rows written.")

    conn.execute("DELETE FROM funnel_landing_pages")
    _insert_df(conn, lp_df, "funnel_landing_pages")
    db_lp = conn.execute("SELECT COUNT(*) FROM funnel_landing_pages").fetchone()[0]
    print(f"  funnel_landing_pages: {db_lp:,} rows written.")

    conn.execute("DELETE FROM funnel_personalization")
    _insert_df(conn, ps_df, "funnel_personalization")
    db_ps = conn.execute("SELECT COUNT(*) FROM funnel_personalization").fetchone()[0]
    print(f"  funnel_personalization: {db_ps:,} rows written.")

    conn.commit()
    conn.close()

    print(f"\nAll funnel tables seeded successfully.")
    print(f"  funnel_events rows:              {db_fe:,}")
    print(f"  funnel_benchmarks rows:          {db_bm:,}")
    print(f"  funnel_abandonment_recovery rows:{db_ab:,}")
    print(f"  funnel_landing_pages rows:       {db_lp:,}")
    print(f"  funnel_personalization rows:     {db_ps:,}")

    return fe_df


if __name__ == "__main__":
    run()
    print("Done.")
