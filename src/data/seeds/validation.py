"""Pandera validation schemas for all seeded tables.

Schemas validate DataFrames produced by each seed module before DB write.
Each public function accepts a DataFrame and raises SchemaError on failure.

Tables covered:
  - campaigns        (seed_campaigns)
  - funnel_events    (seed_funnel)
  - cohorts          (seed_cohorts — APE-48 PFI member rows)
  - kpi_summary      (seed_kpis)
  - alerts           (alerts)
  - budgets          (budgets)
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema, Check
import pandas as pd

# ---------------------------------------------------------------------------
# Shared valid values (must stay in sync with seed modules)
# ---------------------------------------------------------------------------

CAMPAIGN_CHANNELS = [
    # seed_campaigns.py (APE-46 revised channels)
    "life_event", "sem_branded", "sem_nonbranded",
    "paid_social_meta", "paid_social_tiktok", "paid_social_linkedin",
    "ctv_olv", "streaming_audio", "ooh_print", "mover",
    # seed_kpis.py channel set
    "paid_search", "paid_social", "display", "email", "direct_mail",
    "affiliate", "organic",
    # legacy / stub channels
    "social",
]

CAMPAIGN_STATUSES = ["draft", "active", "paused", "completed"]

FUNNEL_STAGES = ["page_visit", "app_start", "form_complete", "kyc_pass", "approval", "funded", "active_90d"]

COHORT_CHANNELS = ["paid_search", "organic", "email", "direct_mail", "referral"]
COHORT_PRODUCTS = ["checking", "savings", "credit_card", "mortgage", "auto_loan"]

KPI_CHANNELS = [
    "paid_search", "paid_social", "display",
    "email", "direct_mail", "affiliate", "organic",
]
KPI_PRODUCTS = [
    "checking", "savings", "credit_card", "mortgage",
    "auto_loan", "personal_loan", "cd", "money_market",
]

# ---------------------------------------------------------------------------
# campaigns
# ---------------------------------------------------------------------------

CAMPAIGNS_SCHEMA = DataFrameSchema(
    {
        "id":         Column(str, nullable=False),
        "name":       Column(str, nullable=False),
        "channel":    Column(str, Check.isin(CAMPAIGN_CHANNELS), nullable=False),
        "status":     Column(str, Check.isin(CAMPAIGN_STATUSES), nullable=False),
        "spend":      Column(float, Check.greater_than_or_equal_to(0), nullable=False),
        "revenue":    Column(float, Check.greater_than_or_equal_to(0), nullable=False),
        "start_date": Column("object", nullable=True),
        "end_date":   Column("object", nullable=True),
    },
    checks=[
        Check(lambda df: len(df) >= 1, error="campaigns: must have at least 1 row"),
    ],
    coerce=True,
)


def validate_campaigns(df: pd.DataFrame) -> pd.DataFrame:
    """Validate campaigns DataFrame. Returns validated df or raises SchemaError."""
    validated = CAMPAIGNS_SCHEMA.validate(df)
    return validated


# ---------------------------------------------------------------------------
# funnel_events
# ---------------------------------------------------------------------------

FUNNEL_CHANNELS = ["Paid Search", "Paid Social", "Display", "Email", "Organic Search", "Direct Mail", "Referral"]
FUNNEL_MARKET_TIERS = ["Tier 1", "Tier 2", "Tier 3"]

FUNNEL_SCHEMA = DataFrameSchema(
    {
        "id":           Column(str, nullable=False),
        "campaign_id":  Column(str, nullable=True),
        "stage":        Column(str, Check.isin(FUNNEL_STAGES), nullable=False),
        "event_date":   Column("object", nullable=False),
        "channel":      Column(str, Check.isin(FUNNEL_CHANNELS), nullable=True),
        "market_tier":  Column(str, Check.isin(FUNNEL_MARKET_TIERS), nullable=True),
        "product_type": Column(str, nullable=True),
        "device":       Column(str, nullable=True),
        "count":        Column(int, Check.greater_than_or_equal_to(0), nullable=False),
    },
    checks=[
        Check(lambda df: len(df) >= 10_000, error="funnel_events: must have >= 10,000 rows"),
        Check(
            lambda df: df["stage"].isin(FUNNEL_STAGES).all(),
            error="funnel_events: all stages must be valid",
        ),
    ],
    coerce=True,
)


def validate_funnel_monotone(df: pd.DataFrame) -> None:
    """Assert stage counts are monotonically non-increasing within each funnel group."""
    errors: list[str] = []
    group_cols = [c for c in ["campaign_id", "market_tier", "event_date"] if c in df.columns]
    groups = df.groupby(group_cols)
    for name, grp in groups:
        ordered = (
            grp.set_index("stage")
            .reindex(FUNNEL_STAGES)["count"]
            .dropna()
            .astype(int)
        )
        for i in range(1, len(ordered)):
            if ordered.iloc[i] > ordered.iloc[i - 1]:
                errors.append(
                    f"{name}: {ordered.index[i]} ({ordered.iloc[i]}) > "
                    f"{ordered.index[i - 1]} ({ordered.iloc[i - 1]})"
                )
    if errors:
        raise ValueError(
            f"Monotone check failed for {len(errors)} group(s):\n" + "\n".join(errors[:10])
        )


def validate_funnel(df: pd.DataFrame, campaign_ids: list[str] | None = None) -> pd.DataFrame:
    """Validate funnel_events DataFrame.

    Args:
        df: funnel_events DataFrame.
        campaign_ids: optional list of valid campaign ids for FK check.

    Returns validated df or raises SchemaError / ValueError.
    """
    validated = FUNNEL_SCHEMA.validate(df)
    if campaign_ids is not None:
        invalid_fks = ~df["campaign_id"].isin(campaign_ids)
        if invalid_fks.any():
            bad = df.loc[invalid_fks, "campaign_id"].unique()[:5]
            raise ValueError(f"funnel_events: invalid campaign_id FK values: {bad.tolist()}")
    validate_funnel_monotone(df)
    return validated


# ---------------------------------------------------------------------------
# cohorts (APE-48 PFI member rows — individual-level, written by seed_cohorts.py)
# ---------------------------------------------------------------------------

COHORTS_PFI_SCHEMA = DataFrameSchema(
    {
        "name":         Column(str, Check(lambda s: s.str.contains(r"\| PFI Member ", regex=True)), nullable=False),
        "segment":      Column(str, Check.isin(COHORT_CHANNELS), nullable=False),
        "size":         Column(int, Check.equal_to(1), nullable=False),
        "period_start": Column(pa.DateTime, nullable=False),
        "period_end":   Column(pa.DateTime, nullable=False),
    },
    checks=[
        Check(lambda df: len(df) >= 5_000, error="cohorts: must have >= 5,000 PFI member rows"),
        Check(
            lambda df: (df["period_end"] > df["period_start"]).all(),
            error="cohorts: period_end must be after period_start",
        ),
    ],
    coerce=True,
)


def validate_cohorts_pfi(df: pd.DataFrame) -> pd.DataFrame:
    """Validate cohorts PFI member DataFrame. Returns validated df or raises SchemaError."""
    return COHORTS_PFI_SCHEMA.validate(df)


# ---------------------------------------------------------------------------
# kpi_summary
# ---------------------------------------------------------------------------

KPI_SUMMARY_SCHEMA = DataFrameSchema(
    {
        "id":               Column(str, nullable=False),
        "period_month":     Column("object", nullable=False),
        "dma":              Column(str, nullable=False),
        "channel":          Column(str, Check.isin(KPI_CHANNELS), nullable=False),
        "product":          Column(str, Check.isin(KPI_PRODUCTS), nullable=False),
        "total_spend":      Column(float, Check.greater_than(0), nullable=False),
        "revenue":          Column(float, Check.greater_than(0), nullable=False),
        "roas":             Column(float, Check.greater_than(0), nullable=False),
        "conversions":      Column(int,   Check.greater_than(0), nullable=False),
        "funnel_volume":    Column(int,   Check.greater_than(0), nullable=False),
        "conversion_rate":  Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "cpa":              Column(float, Check.greater_than(0), nullable=False),
        "funded_accounts":  Column(int,   Check.greater_than(0), nullable=False),
        "cost_per_funded":  Column(float, Check.greater_than(0), nullable=False),
        "mob6_retention":   Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "mob12_retention":  Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "ltv":              Column(float, Check.greater_than(0), nullable=False),
        "net_margin":       Column(float, Check.in_range(-1.0, 1.0), nullable=False),
        "active_customers": Column(int,   Check.greater_than(0), nullable=False),
        "nps":              Column(float, Check.in_range(-100, 100), nullable=False),
    },
    checks=[
        Check(lambda df: len(df) >= 10_000, error="kpi_summary: must have >= 10,000 rows"),
        Check(
            lambda df: df["dma"].nunique() >= 10,
            error="kpi_summary: must span >= 10 distinct DMAs",
        ),
        Check(
            lambda df: len(
                [c for c in [
                    "total_spend", "revenue", "roas", "conversions",
                    "funnel_volume", "conversion_rate", "cpa",
                    "funded_accounts", "cost_per_funded", "mob6_retention",
                    "mob12_retention", "ltv", "net_margin",
                    "active_customers", "nps",
                ] if c in df.columns]
            ) >= 10,
            error="kpi_summary: must have >= 10 KPI columns",
        ),
    ],
    coerce=True,
)


def validate_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """Validate kpi_summary DataFrame. Returns validated df or raises SchemaError."""
    return KPI_SUMMARY_SCHEMA.validate(df)


# ---------------------------------------------------------------------------
# alerts
# ---------------------------------------------------------------------------

ALERT_SEVERITIES = ["info", "warning", "critical"]
ALERT_CATEGORIES = ["performance", "budget", "competitor", "system"]

ALERTS_SCHEMA = DataFrameSchema(
    {
        "id":          Column(str, nullable=False),
        "title":       Column(str, nullable=False),
        "severity":    Column(str, Check.isin(ALERT_SEVERITIES), nullable=False),
        "category":    Column(str, Check.isin(ALERT_CATEGORIES), nullable=False),
        "message":     Column(str, nullable=False),
        "is_read":     Column(bool, nullable=False),
        "resolved_at": Column("object", nullable=True),
        "created_at":  Column("object", nullable=False),
        "updated_at":  Column("object", nullable=False),
    },
    checks=[
        Check(lambda df: len(df) >= 30, error="alerts: must have >= 30 rows"),
        Check(lambda df: (df["severity"] == "critical").sum() >= 3, error="alerts: must have >= 3 critical alerts"),
        Check(lambda df: (df["severity"] == "warning").sum() >= 10, error="alerts: must have >= 10 warning alerts"),
        Check(lambda df: (df["severity"] == "info").sum() >= 15, error="alerts: must have >= 15 info alerts"),
    ],
    coerce=True,
)


def validate_alerts(df: pd.DataFrame) -> pd.DataFrame:
    """Validate alerts DataFrame. Returns validated df or raises SchemaError."""
    return ALERTS_SCHEMA.validate(df)


# ---------------------------------------------------------------------------
# budgets
# ---------------------------------------------------------------------------

BUDGET_CHANNELS = [
    "brand_media", "paid_search", "paid_social",
    "high_value_overlay", "seo_aeo", "conversion_testing",
]

BUDGET_PERIODS = ["monthly", "quarterly", "annual"]

BUDGET_SCHEMA = DataFrameSchema(
    {
        "id":           Column(str, nullable=False),
        "name":         Column(str, nullable=False),
        "channel":      Column(str, Check.isin(BUDGET_CHANNELS), nullable=False),
        "period":       Column(str, Check.isin(BUDGET_PERIODS), nullable=False),
        "period_start": Column("object", nullable=False),
        "allocated":    Column(float, Check.greater_than(0), nullable=False),
        "actual":       Column(float, Check.greater_than(0), nullable=False),
    },
    checks=[
        Check(lambda df: len(df) >= 72, error="budgets: must have >= 72 rows"),
        Check(lambda df: df["channel"].nunique() == 6, error="budgets: must have 6 distinct channels"),
        Check(
            lambda df: df.groupby("channel")["period_start"].nunique().eq(12).all(),
            error="budgets: each channel must have exactly 12 monthly entries",
        ),
        Check(
            lambda df: abs(df["allocated"].sum() - 15_000_000.0) < 1.0,
            error="budgets: sum of allocated must equal $15,000,000 (±$1)",
        ),
        Check(
            lambda df: (
                (df["actual"] / df["allocated"]).between(0.92, 1.08)
            ).all(),
            error="budgets: actual/allocated ratio must be within ±8% band",
        ),
    ],
    coerce=True,
)


def validate_budgets(df: pd.DataFrame) -> pd.DataFrame:
    """Validate budgets DataFrame. Returns validated df or raises SchemaError."""
    return BUDGET_SCHEMA.validate(df)


# ---------------------------------------------------------------------------
# budget_pacing
# ---------------------------------------------------------------------------

PACING_CHANNELS = [
    "brand_media", "paid_search", "paid_social",
    "high_value_overlay", "seo_aeo", "conversion_testing",
]
PACING_STATUSES = ["on_track", "over", "under"]

BUDGET_PACING_SCHEMA = DataFrameSchema(
    {
        "id":                 Column(str, nullable=False),
        "channel":            Column(str, Check.isin(PACING_CHANNELS), nullable=False),
        "period_month":       Column("object", nullable=False),
        "week_num":           Column(int, Check.isin([1, 2, 3, 4]), nullable=False),
        "week_start":         Column("object", nullable=False),
        "weekly_planned":     Column(float, Check.greater_than(0), nullable=False),
        "weekly_actual":      Column(float, Check.greater_than_or_equal_to(0), nullable=False),
        "cumulative_planned": Column(float, Check.greater_than(0), nullable=False),
        "cumulative_actual":  Column(float, Check.greater_than_or_equal_to(0), nullable=False),
        "pacing_rate":        Column(float, Check.in_range(0.5, 2.0), nullable=False),
        "forecast_eom":       Column(float, Check.greater_than_or_equal_to(0), nullable=False),
        "variance_pct":       Column(float, nullable=False),
        "pacing_status":      Column(str, Check.isin(PACING_STATUSES), nullable=False),
    },
    checks=[
        Check(lambda df: len(df) == 288, error="budget_pacing: expected 288 rows"),
        Check(lambda df: df["channel"].nunique() == 6, error="budget_pacing: expected 6 channels"),
        Check(
            lambda df: df.groupby(["channel", "period_month"])["week_num"].nunique().eq(4).all(),
            error="budget_pacing: each channel×month must have 4 weekly entries",
        ),
    ],
    coerce=True,
)


def validate_budget_pacing(df: pd.DataFrame) -> pd.DataFrame:
    """Validate budget_pacing DataFrame. Returns validated df or raises SchemaError."""
    return BUDGET_PACING_SCHEMA.validate(df)


# ---------------------------------------------------------------------------
# markets
# ---------------------------------------------------------------------------

MARKETS_TIERS = [1, 2, 3]

MARKETS_SCHEMA = DataFrameSchema(
    {
        "id":                      Column(str, nullable=False),
        "dma_code":                Column(str, nullable=False),
        "dma_name":                Column(str, nullable=False),
        "tier":                    Column(int, Check.isin(MARKETS_TIERS), nullable=False),
        "state":                   Column(str, nullable=False),
        "population":              Column(int, Check.greater_than(0), nullable=False),
        "hhi_median":              Column(int, Check.greater_than(0), nullable=False),
        "branch_count":            Column(int, Check.greater_than_or_equal_to(1), nullable=False),
        "digital_adoption_pct":    Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "brand_awareness_pct":     Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "brand_consideration_pct": Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "brand_health_score":      Column(float, Check.in_range(0.0, 100.0), nullable=False),
        "retention_6m":            Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "retention_12m":           Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "nps_score":               Column(float, Check.in_range(-100.0, 100.0), nullable=False),
        "active_customers":        Column(int, Check.greater_than(0), nullable=False),
        "avg_ltv":                 Column(float, Check.greater_than(0), nullable=False),
    },
    checks=[
        Check(lambda df: len(df) == 20, error="markets: expected 20 DMA rows"),
        Check(lambda df: df["dma_code"].nunique() == 20, error="markets: dma_code must be unique"),
        Check(
            lambda df: (df["retention_12m"] <= df["retention_6m"]).all(),
            error="markets: retention_12m must be <= retention_6m",
        ),
        Check(
            lambda df: (df["brand_consideration_pct"] <= df["brand_awareness_pct"]).all(),
            error="markets: consideration must be <= awareness",
        ),
    ],
    coerce=True,
)


def validate_markets(df: pd.DataFrame) -> pd.DataFrame:
    """Validate markets DataFrame. Returns validated df or raises SchemaError."""
    return MARKETS_SCHEMA.validate(df)


# ---------------------------------------------------------------------------
# channel_mix
# ---------------------------------------------------------------------------

MIX_CHANNELS = [
    "brand_media", "paid_search", "paid_social",
    "high_value_overlay", "seo_aeo", "conversion_testing",
]
MIX_PRODUCTS = [
    "checking", "savings", "credit_card", "mortgage", "auto_loan",
    "personal_loan", "cd", "money_market",
]

CHANNEL_MIX_SCHEMA = DataFrameSchema(
    {
        "id":                   Column(str, nullable=False),
        "channel":              Column(str, Check.isin(MIX_CHANNELS), nullable=False),
        "product":              Column(str, Check.isin(MIX_PRODUCTS), nullable=False),
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
        Check(lambda df: len(df) == 48, error="channel_mix: expected 48 rows (6 channels × 8 products)"),
        Check(lambda df: df["channel"].nunique() == 6, error="channel_mix: expected 6 channels"),
        Check(lambda df: df["product"].nunique() == 8, error="channel_mix: expected 8 products"),
        Check(
            lambda df: (
                df.groupby("product")["baseline_mix_pct"]
                .sum()
                .apply(lambda s: abs(s - 1.0) < 0.001)
                .all()
            ),
            error="channel_mix: baseline_mix_pct must sum to 1.0 per product (±0.001)",
        ),
    ],
    coerce=True,
)


def validate_channel_mix(df: pd.DataFrame) -> pd.DataFrame:
    """Validate channel_mix DataFrame. Returns validated df or raises SchemaError."""
    return CHANNEL_MIX_SCHEMA.validate(df)


# ---------------------------------------------------------------------------
# sem_keyword_groups  (APE-97)
# ---------------------------------------------------------------------------

SEM_INTENT_TYPES = ["branded", "non_branded", "pmax", "conquesting"]
SEM_MATCH_TYPES  = ["broad", "exact", "phrase"]
SEM_PRODUCTS     = [
    "checking", "savings", "credit_card", "mortgage",
    "auto_loan", "personal_loan", "cd", "money_market",
]
SEM_STATUSES = ["active", "paused", "deleted"]
SEM_BUDGET   = 3_750_000.0  # 25% of $15M total media budget

SEM_KEYWORD_GROUPS_SCHEMA = DataFrameSchema(
    {
        "id":                       Column(str, nullable=False),
        "name":                     Column(str, nullable=False),
        "product_category":         Column(str, Check.isin(SEM_PRODUCTS), nullable=False),
        "intent_type":              Column(str, Check.isin(SEM_INTENT_TYPES), nullable=False),
        "match_type":               Column(str, Check.isin(SEM_MATCH_TYPES), nullable=False),
        "max_cpc":                  Column(float, Check.in_range(0.40, 6.00), nullable=False),
        "quality_score":            Column(int, Check.in_range(1, 10), nullable=False),
        "estimated_monthly_volume": Column(int, Check.greater_than(0), nullable=False),
        "status":                   Column(str, Check.isin(SEM_STATUSES), nullable=False),
    },
    checks=[
        Check(lambda df: len(df) >= 200,
              error="sem_keyword_groups: must have >= 200 groups"),
        Check(
            lambda df: abs(
                df[df["intent_type"] == "branded"].shape[0] / len(df) - 0.40
            ) < 0.05,
            error="sem_keyword_groups: branded share must be ~40% (±5%) — matches budget_share",
        ),
        Check(
            lambda df: abs(
                df[df["intent_type"] == "non_branded"].shape[0] / len(df) - 0.45
            ) < 0.05,
            error="sem_keyword_groups: non_branded share must be ~45% (±5%)",
        ),
        Check(
            lambda df: (
                abs(df[df["match_type"] == "broad"].shape[0]  / len(df) - 0.30) < 0.05 and
                abs(df[df["match_type"] == "exact"].shape[0]  / len(df) - 0.45) < 0.05 and
                abs(df[df["match_type"] == "phrase"].shape[0] / len(df) - 0.25) < 0.05
            ),
            error="sem_keyword_groups: match type distribution must be ~broad 30%/exact 45%/phrase 25%",
        ),
    ],
    coerce=True,
)


def validate_sem_keyword_groups(df: pd.DataFrame) -> pd.DataFrame:
    """Validate sem_keyword_groups DataFrame. Returns validated df or raises SchemaError."""
    return SEM_KEYWORD_GROUPS_SCHEMA.validate(df)


# ---------------------------------------------------------------------------
# sem_daily_performance  (APE-97)
# ---------------------------------------------------------------------------

SEM_DAILY_PERFORMANCE_SCHEMA = DataFrameSchema(
    {
        "id":                  Column(str, nullable=False),
        "keyword_group_id":    Column(str, nullable=False),
        "record_date":         Column("object", nullable=False),
        "impressions":         Column(int, Check.greater_than(0), nullable=False),
        "clicks":              Column(int, Check.greater_than(0), nullable=False),
        "ctr":                 Column(float, Check.in_range(0.0, 0.50), nullable=False),
        "avg_cpc":             Column(float, Check.in_range(0.40, 6.00), nullable=False),
        "spend":               Column(float, Check.greater_than(0), nullable=False),
        "avg_position":        Column(float, Check.in_range(1.0, 8.0), nullable=False),
        "impression_share":    Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "quality_score":       Column(int, Check.in_range(1, 10), nullable=False),
        "conversions":         Column(int, Check.greater_than_or_equal_to(0), nullable=False),
        "conversion_rate":     Column(float, Check.in_range(0.0, 0.20), nullable=False),
        "cost_per_conversion": Column(float, Check.greater_than(0), nullable=False),
    },
    checks=[
        Check(
            lambda df: len(df) >= 18_000,
            error="sem_daily_performance: must have >= 18,000 rows (200 groups × 90 days)",
        ),
        Check(
            lambda df: abs(df["spend"].sum() - SEM_BUDGET) < 1.0,
            error=f"sem_daily_performance: total spend must equal ${SEM_BUDGET:,.2f} (±$1)",
        ),
        Check(
            lambda df: (df["clicks"] <= df["impressions"]).all(),
            error="sem_daily_performance: clicks must not exceed impressions",
        ),
        Check(
            lambda df: df["keyword_group_id"].nunique() >= 200,
            error="sem_daily_performance: must have >= 200 distinct keyword groups",
        ),
    ],
    coerce=True,
)


def validate_sem_daily_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Validate sem_daily_performance DataFrame. Returns validated df or raises SchemaError."""
    return SEM_DAILY_PERFORMANCE_SCHEMA.validate(df)


# ---------------------------------------------------------------------------
# social_paid_daily  (APE-98)
# ---------------------------------------------------------------------------

SOCIAL_PLATFORMS = ["Meta", "TikTok", "LinkedIn", "Other"]
SOCIAL_TOTAL_MEDIA_BUDGET = 15_000_000.0
SOCIAL_TARGET_SPEND = SOCIAL_TOTAL_MEDIA_BUDGET * 0.15  # $2,250,000

SOCIAL_PAID_DAILY_SCHEMA = DataFrameSchema(
    {
        "id":            Column(str,   nullable=False),
        "platform":      Column(str,   Check.isin(SOCIAL_PLATFORMS), nullable=False),
        "record_date":   Column("object", nullable=False),
        "spend":         Column(float, Check.greater_than(0), nullable=False),
        "impressions":   Column(int,   Check.greater_than_or_equal_to(0), nullable=False),
        "clicks":        Column(int,   Check.greater_than_or_equal_to(0), nullable=False),
        "ctr":           Column(float, Check.in_range(0.0, 0.20), nullable=False),
        "cvr_native":    Column(float, Check.in_range(0.08, 0.22), nullable=False),
        "cvr_landing":   Column(float, Check.in_range(0.02, 0.07), nullable=False),
        "leads_native":  Column(int,   Check.greater_than_or_equal_to(0), nullable=False),
        "leads_landing": Column(int,   Check.greater_than_or_equal_to(0), nullable=False),
        "total_leads":   Column(int,   Check.greater_than_or_equal_to(0), nullable=False),
        "cpa_native":    Column(float, Check.greater_than(0), nullable=False),
        "cpa_landing":   Column(float, Check.greater_than(0), nullable=False),
    },
    checks=[
        Check(
            lambda df: len(df) == 360,
            error="social_paid_daily: expected 360 rows (4 platforms × 90 days)",
        ),
        Check(
            lambda df: df["platform"].nunique() == 4,
            error="social_paid_daily: must have all 4 platforms",
        ),
        Check(
            lambda df: abs(df["spend"].sum() - SOCIAL_TARGET_SPEND) < 1.0,
            error=f"social_paid_daily: total spend must reconcile to ${SOCIAL_TARGET_SPEND:,.0f} (±$1)",
        ),
        Check(
            lambda df: (
                df[df["platform"] == "Meta"]["spend"].sum() / df["spend"].sum()
            ) >= 0.68,
            error="social_paid_daily: Meta spend share must be ≥68% (target 70%)",
        ),
    ],
    coerce=True,
)


def validate_social_paid_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Validate social_paid_daily DataFrame. Returns validated df or raises SchemaError."""
    return SOCIAL_PAID_DAILY_SCHEMA.validate(df)


# ---------------------------------------------------------------------------
# social_paid_creatives  (APE-98)
# ---------------------------------------------------------------------------

SOCIAL_CREATIVE_FORMATS = ["video", "static", "carousel"]
SOCIAL_CAMPAIGN_TYPES = ["awareness", "consideration", "conversion", "retargeting"]
SOCIAL_CREATIVE_STATUSES = ["active", "paused", "completed"]

SOCIAL_PAID_CREATIVES_SCHEMA = DataFrameSchema(
    {
        "id":            Column(str,   nullable=False),
        "creative_id":   Column(str,   nullable=False),
        "platform":      Column(str,   Check.isin(SOCIAL_PLATFORMS), nullable=False),
        "format":        Column(str,   Check.isin(SOCIAL_CREATIVE_FORMATS), nullable=False),
        "campaign_type": Column(str,   Check.isin(SOCIAL_CAMPAIGN_TYPES), nullable=False),
        "ctr":           Column(float, Check.in_range(0.0, 0.10), nullable=False),
        "cvr":           Column(float, Check.in_range(0.08, 0.22), nullable=False),
        "spend":         Column(float, Check.greater_than(0), nullable=False),
        "impressions":   Column(int,   Check.greater_than(0), nullable=False),
        "clicks":        Column(int,   Check.greater_than_or_equal_to(0), nullable=False),
        "conversions":   Column(int,   Check.greater_than_or_equal_to(0), nullable=False),
        "status":        Column(str,   Check.isin(SOCIAL_CREATIVE_STATUSES), nullable=False),
    },
    checks=[
        Check(
            lambda df: len(df) >= 50,
            error="social_paid_creatives: must have >= 50 creative records",
        ),
        Check(
            lambda df: df["platform"].nunique() == 4,
            error="social_paid_creatives: must represent all 4 platforms",
        ),
        Check(
            lambda df: df["format"].nunique() >= 2,
            error="social_paid_creatives: must have >= 2 creative formats",
        ),
    ],
    coerce=True,
)


def validate_social_paid_creatives(df: pd.DataFrame) -> pd.DataFrame:
    """Validate social_paid_creatives DataFrame. Returns validated df or raises SchemaError."""
    return SOCIAL_PAID_CREATIVES_SCHEMA.validate(df)


# ---------------------------------------------------------------------------
# social_paid_audiences  (APE-98)
# ---------------------------------------------------------------------------

SOCIAL_AUDIENCE_SEGMENT_TYPES = [
    "custom_list", "lookalike", "interest", "retargeting",
    "crm_match", "behavioral", "demographic",
]

SOCIAL_PAID_AUDIENCES_SCHEMA = DataFrameSchema(
    {
        "id":               Column(str,   nullable=False),
        "audience_name":    Column(str,   nullable=False),
        "platform":         Column(str,   Check.isin(SOCIAL_PLATFORMS), nullable=False),
        "segment_type":     Column(str,   Check.isin(SOCIAL_AUDIENCE_SEGMENT_TYPES), nullable=False),
        "size":             Column(int,   Check.greater_than(0), nullable=False),
        "match_rate":       Column(float, Check.in_range(0.30, 0.90), nullable=False),
        "performance_lift": Column(float, Check.greater_than_or_equal_to(1.0), nullable=False),
        "status":           Column(str,   Check.isin(["active", "paused"]), nullable=False),
    },
    checks=[
        Check(
            lambda df: 12 <= len(df) <= 20,
            error="social_paid_audiences: must have 12–20 segments",
        ),
        Check(
            lambda df: (df["status"] == "active").sum() >= 12,
            error="social_paid_audiences: must have >= 12 active segments",
        ),
        Check(
            lambda df: df["performance_lift"].gt(1.0).any(),
            error="social_paid_audiences: at least one segment must show >1.0 lift",
        ),
    ],
    coerce=True,
)


def validate_social_paid_audiences(df: pd.DataFrame) -> pd.DataFrame:
    """Validate social_paid_audiences DataFrame. Returns validated df or raises SchemaError."""
    return SOCIAL_PAID_AUDIENCES_SCHEMA.validate(df)


# ---------------------------------------------------------------------------
# brand_media_bei_weekly  (APE-99)
# ---------------------------------------------------------------------------

BRAND_MEDIA_TIERS = ["Growth", "Maintain", "Experiment"]

BRAND_MEDIA_BEI_WEEKLY_SCHEMA = DataFrameSchema(
    {
        "id":                  Column(str, nullable=False),
        "market_name":         Column(str, nullable=False),
        "market_tier":         Column(str, Check.isin(BRAND_MEDIA_TIERS), nullable=False),
        "week_ending":         Column("object", nullable=False),
        "awareness_score":     Column(float, Check.in_range(10, 100), nullable=False),
        "consideration_score": Column(float, Check.in_range(10, 100), nullable=False),
        "preference_score":    Column(float, Check.in_range(10, 100), nullable=False),
        "advocacy_score":      Column(float, Check.in_range(10, 100), nullable=False),
        "bei_score":           Column(float, Check.in_range(10, 100), nullable=False),
    },
    checks=[
        Check(lambda df: len(df) == 180, error="brand_media_bei_weekly: expected 180 rows"),
        Check(
            lambda df: df["market_tier"].nunique() == 3,
            error="brand_media_bei_weekly: must have 3 market tiers",
        ),
    ],
    coerce=True,
)


def validate_brand_media_bei_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """Validate brand_media_bei_weekly DataFrame."""
    return BRAND_MEDIA_BEI_WEEKLY_SCHEMA.validate(df)


# ---------------------------------------------------------------------------
# brand_media_performance  (APE-99)
# ---------------------------------------------------------------------------

BRAND_MEDIA_PERFORMANCE_SCHEMA = DataFrameSchema(
    {
        "id":                   Column(str, nullable=False),
        "market_name":          Column(str, nullable=False),
        "market_tier":          Column(str, Check.isin(BRAND_MEDIA_TIERS), nullable=False),
        "week_ending":          Column("object", nullable=False),
        "spend":                Column(float, Check.greater_than(0), nullable=False),
        "impressions":          Column(int, Check.greater_than(0), nullable=False),
        "ctv_15s_completion":   Column(float, Check.in_range(0.75, 1.0), nullable=False),
        "ctv_30s_completion":   Column(float, Check.in_range(0.75, 1.0), nullable=False),
        "olv_15s_completion":   Column(float, Check.in_range(0.75, 1.0), nullable=False),
        "olv_30s_completion":   Column(float, Check.in_range(0.75, 1.0), nullable=False),
        "audio_listen_through": Column(float, Check.in_range(0.60, 0.95), nullable=False),
        "frequency_compliance": Column(float, Check.in_range(0.50, 1.0), nullable=False),
    },
    checks=[
        Check(lambda df: len(df) == 180, error="brand_media_performance: expected 180 rows"),
        Check(
            lambda df: abs(df["spend"].sum() - 6_000_000.0) < 10.0,
            error="brand_media_performance: total spend must equal $6,000,000 (±$10)",
        ),
    ],
    coerce=True,
)


def validate_brand_media_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Validate brand_media_performance DataFrame."""
    return BRAND_MEDIA_PERFORMANCE_SCHEMA.validate(df)


# ---------------------------------------------------------------------------
# brand_media_incrementality_pairs  (APE-99)
# ---------------------------------------------------------------------------

BRAND_MEDIA_INCREMENTALITY_SCHEMA = DataFrameSchema(
    {
        "id":               Column(str, nullable=False),
        "pair_name":        Column(str, nullable=False),
        "active_market":    Column(str, nullable=False),
        "control_market":   Column(str, nullable=False),
        "test_start_date":  Column("object", nullable=False),
        "test_end_date":    Column("object", nullable=False),
        "observed_lift":    Column(float, Check.in_range(0.0, 0.50), nullable=False),
        "confidence_level": Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "p_value":          Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "is_significant":   Column(bool, nullable=False),
        "sample_size":      Column(int, Check.greater_than(0), nullable=False),
    },
    checks=[
        Check(
            lambda df: 5 <= len(df) <= 8,
            error="brand_media_incrementality_pairs: must have 5–8 pairs",
        ),
        Check(
            lambda df: 3 <= df["is_significant"].sum() <= 5,
            error="brand_media_incrementality_pairs: must have 3–5 significant pairs",
        ),
        Check(
            lambda df: df[df["is_significant"]]["p_value"].max() < 0.05,
            error="brand_media_incrementality_pairs: all significant pairs must have p_value < 0.05",
        ),
    ],
    coerce=True,
)


def validate_brand_media_incrementality(df: pd.DataFrame) -> pd.DataFrame:
    """Validate brand_media_incrementality_pairs DataFrame."""
    return BRAND_MEDIA_INCREMENTALITY_SCHEMA.validate(df)


# ---------------------------------------------------------------------------
# life_events (APE-100)
# ---------------------------------------------------------------------------

LIFE_EVENT_CAMPAIGN_NAMES = [
    "New Mover",
    "New Homeowner",
    "New Parent",
    "Marriage",
    "Retirement",
    "College",
    "Job Change",
    "Inheritance/Wealth Transfer",
]

LIFE_EVENT_DATA_PROVIDERS = ["CoreLogic", "Experian", "LexisNexis", "Acxiom", "TransUnion"]

_OVERLAY_BUDGET = 15_000_000.0 * 0.12  # $1,800,000

LIFE_EVENT_CAMPAIGN_PERFORMANCE_SCHEMA = DataFrameSchema(
    {
        "id":               Column(str, nullable=False),
        "campaign_id":      Column(str, nullable=False),
        "campaign_name":    Column(str, Check.isin(LIFE_EVENT_CAMPAIGN_NAMES), nullable=False),
        "channel":          Column(str, nullable=False),
        "event_date":       Column("object", nullable=False),
        "impressions":      Column(int, Check.greater_than_or_equal_to(0), nullable=False),
        "clicks":           Column(int, Check.greater_than_or_equal_to(0), nullable=False),
        "conversions":      Column(int, Check.greater_than_or_equal_to(0), nullable=False),
        "spend":            Column(float, Check.greater_than_or_equal_to(0), nullable=False),
        "ctr":              Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "cvr":              Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "cpa":              Column(float, Check.greater_than_or_equal_to(0), nullable=False),
        "cvr_vs_baseline":  Column(float, Check.in_range(1.0, 10.0), nullable=False),
    },
    checks=[
        Check(
            lambda df: df["campaign_name"].nunique() == 8,
            error="life_event_campaign_performance: must have 8 distinct campaigns",
        ),
        Check(
            lambda df: df.groupby("campaign_name")["cvr_vs_baseline"].mean().between(1.9, 4.1).all(),
            error="life_event_campaign_performance: mean cvr_vs_baseline must be 2-4x per campaign",
        ),
        Check(
            lambda df: abs(df["spend"].sum() - _OVERLAY_BUDGET) < 1.0,
            error="life_event_campaign_performance: total spend must equal $1,800,000 (+-$1)",
        ),
    ],
    coerce=True,
)

LIFE_EVENT_MOVER_PIPELINE_SCHEMA = DataFrameSchema(
    {
        "id":                  Column(str, nullable=False),
        "week_num":            Column(int, Check.in_range(1, 12), nullable=False),
        "week_start":          Column("object", nullable=False),
        "dma_code":            Column(str, nullable=False),
        "dma_name":            Column(str, nullable=False),
        "data_provider":       Column(str, Check.isin(LIFE_EVENT_DATA_PROVIDERS), nullable=False),
        "pipeline_volume":     Column(int, Check.greater_than(0), nullable=False),
        "match_rate":          Column(float, Check.in_range(0.50, 0.90), nullable=False),
        "matched_records":     Column(int, Check.greater_than_or_equal_to(0), nullable=False),
        "propensity_cvr_mult": Column(float, Check.in_range(3.0, 7.0), nullable=False),
        "mover_cvr":           Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "conversions_est":     Column(int, Check.greater_than_or_equal_to(0), nullable=False),
    },
    checks=[
        Check(
            lambda df: (df["matched_records"] <= df["pipeline_volume"]).all(),
            error="life_event_mover_pipeline: matched_records must not exceed pipeline_volume",
        ),
    ],
    coerce=True,
)


def validate_life_event_campaigns(df: pd.DataFrame) -> pd.DataFrame:
    """Validate life_event_campaign_performance DataFrame."""
    return LIFE_EVENT_CAMPAIGN_PERFORMANCE_SCHEMA.validate(df)


def validate_life_event_mover_pipeline(df: pd.DataFrame) -> pd.DataFrame:
    """Validate life_event_mover_pipeline DataFrame."""
    return LIFE_EVENT_MOVER_PIPELINE_SCHEMA.validate(df)


# ---------------------------------------------------------------------------
# aeo_weekly_readings  (APE-101)
# ---------------------------------------------------------------------------

AEO_PLATFORMS = ["ChatGPT", "Perplexity", "Gemini", "Claude", "Copilot", "Meta AI"]

AEO_WEEKLY_SCHEMA = DataFrameSchema(
    {
        "id":              Column(str, nullable=False),
        "week_ending":     Column("object", nullable=False),
        "platform":        Column(str, Check.isin(AEO_PLATFORMS), nullable=False),
        "prompt":          Column(str, nullable=False),
        "mention_rate":    Column(float, Check.in_range(0.15, 0.60), nullable=False),
        "avg_position":    Column(float, Check.in_range(1.0, 5.0), nullable=False),
        "share_of_voice":  Column(float, Check.in_range(0.05, 0.25), nullable=False),
        "sentiment_score": Column(float, Check.in_range(0.20, 0.80), nullable=False),
        "citation_rate":   Column(float, Check.in_range(0.10, 0.40), nullable=False),
    },
    checks=[
        Check(lambda df: len(df) == 3_600, error="aeo_weekly_readings: expected 3,600 rows (6×50×12)"),
        Check(lambda df: df["platform"].nunique() == 6, error="aeo_weekly_readings: expected 6 platforms"),
        Check(lambda df: df["prompt"].nunique() == 50, error="aeo_weekly_readings: expected 50 prompts"),
        Check(lambda df: df["week_ending"].nunique() == 12, error="aeo_weekly_readings: expected 12 weeks"),
        Check(
            lambda df: (
                df.groupby("week_ending")["mention_rate"].mean().iloc[-1]
                > df.groupby("week_ending")["mention_rate"].mean().iloc[0]
            ),
            error="aeo_weekly_readings: client bank mention rate should improve over time",
        ),
    ],
    coerce=True,
)


def validate_aeo_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """Validate aeo_weekly_readings DataFrame."""
    return AEO_WEEKLY_SCHEMA.validate(df)


# ---------------------------------------------------------------------------
# aeo_competitor_scores  (APE-101)
# ---------------------------------------------------------------------------

AEO_COMPETITORS = [
    "National Bank A",
    "Regional Bank B",
    "Digital Bank C",
    "Credit Union D",
    "National Bank E",
]

AEO_COMPETITOR_SCHEMA = DataFrameSchema(
    {
        "id":               Column(str, nullable=False),
        "week_ending":      Column("object", nullable=False),
        "competitor_name":  Column(str, Check.isin(AEO_COMPETITORS), nullable=False),
        "platform":         Column(str, Check.isin(AEO_PLATFORMS), nullable=False),
        "mention_rate":     Column(float, Check.in_range(0.15, 0.60), nullable=False),
        "avg_position":     Column(float, Check.in_range(1.0, 5.0), nullable=False),
        "share_of_voice":   Column(float, Check.in_range(0.05, 0.25), nullable=False),
        "sentiment_score":  Column(float, Check.in_range(0.20, 0.80), nullable=False),
        "citation_rate":    Column(float, Check.in_range(0.10, 0.40), nullable=False),
    },
    checks=[
        Check(lambda df: len(df) == 360, error="aeo_competitor_scores: expected 360 rows (5×6×12)"),
        Check(lambda df: df["competitor_name"].nunique() == 5, error="aeo_competitor_scores: expected 5 competitors"),
        Check(lambda df: df["platform"].nunique() == 6, error="aeo_competitor_scores: expected 6 platforms"),
        Check(lambda df: df["week_ending"].nunique() == 12, error="aeo_competitor_scores: expected 12 weeks"),
    ],
    coerce=True,
)


def validate_aeo_competitors(df: pd.DataFrame) -> pd.DataFrame:
    """Validate aeo_competitor_scores DataFrame."""
    return AEO_COMPETITOR_SCHEMA.validate(df)


# ---------------------------------------------------------------------------
# llm_visibility  (APE-84 / APE-18b)
# ---------------------------------------------------------------------------

LLM_PLATFORMS = [
    "google_ai_overviews",
    "chatgpt",
    "perplexity",
    "gemini",
    "claude",
    "copilot",
]

LLM_BRANDS = [
    "Fifth Third Bank",
    "National Bank A",
    "Regional Bank B",
    "Digital Bank C",
    "Credit Union D",
    "National Bank E",
]

LLM_VISIBILITY_SCHEMA = DataFrameSchema(
    {
        "id":               Column(str, nullable=False),
        "week_start":       Column("object", nullable=False),
        "platform":         Column(str, Check.isin(LLM_PLATFORMS), nullable=False),
        "prompt_text":      Column(str, nullable=False),
        "prompt_category":  Column(str, nullable=False),
        "market_dma":       Column(str, nullable=False),
        "brand":            Column(str, Check.isin(LLM_BRANDS), nullable=False),
        "mentioned":        Column(bool, nullable=False),
        "position":         Column(float, Check.in_range(1.0, 5.0), nullable=True),
        "mention_rate":     Column(float, Check.in_range(0.15, 0.60), nullable=False),
        "sentiment_score":  Column(float, Check.in_range(0.20, 0.80), nullable=False),
        "citation_rate":    Column(float, Check.in_range(0.10, 0.40), nullable=False),
    },
    checks=[
        Check(lambda df: len(df) == 21_600,
              error="llm_visibility: expected 21,600 rows (6 brands × 6 platforms × 50 prompts × 12 weeks)"),
        Check(lambda df: df["brand"].nunique() == 6,
              error="llm_visibility: expected 6 brands"),
        Check(lambda df: df["platform"].nunique() == 6,
              error="llm_visibility: expected 6 platforms"),
        Check(lambda df: df["prompt_text"].nunique() == 50,
              error="llm_visibility: expected 50 prompts"),
        Check(lambda df: df["week_start"].nunique() == 12,
              error="llm_visibility: expected 12 weeks"),
        Check(lambda df: df["market_dma"].nunique() == 22,
              error="llm_visibility: expected 22 DMAs"),
    ],
    coerce=True,
)


def validate_llm_visibility(df: pd.DataFrame) -> pd.DataFrame:
    """Validate llm_visibility DataFrame."""
    return LLM_VISIBILITY_SCHEMA.validate(df)


# ---------------------------------------------------------------------------
# seo_rankings  (APE-84 / APE-18b)
# ---------------------------------------------------------------------------

SEO_CATEGORIES = [
    "checking", "savings", "mortgage",
    "credit_card", "auto_loan", "personal_loan",
]

SEO_RANKINGS_SCHEMA = DataFrameSchema(
    {
        "id":               Column(str, nullable=False),
        "week_start":       Column("object", nullable=False),
        "keyword":          Column(str, nullable=False),
        "product_category": Column(str, Check.isin(SEO_CATEGORIES), nullable=False),
        "rank_position":    Column(int, Check.greater_than_or_equal_to(1), nullable=False),
        "rank_page":        Column(int, Check.greater_than_or_equal_to(1), nullable=False),
        "search_volume":    Column(int, Check.greater_than_or_equal_to(0), nullable=False),
        "rank_change":      Column(int, nullable=False),
    },
    checks=[
        Check(lambda df: len(df) == 2_400,
              error="seo_rankings: expected 2,400 rows (200 keywords × 12 weeks)"),
        Check(lambda df: df["keyword"].nunique() == 200,
              error="seo_rankings: expected 200 unique keywords"),
        Check(lambda df: df["week_start"].nunique() == 12,
              error="seo_rankings: expected 12 weeks"),
        Check(
            lambda df: 0.20 <= (df["rank_page"] == 1).mean() <= 0.45,
            error="seo_rankings: page 1 share should be roughly 20–45%",
        ),
    ],
    coerce=True,
)


def validate_seo_rankings(df: pd.DataFrame) -> pd.DataFrame:
    """Validate seo_rankings DataFrame."""
    return SEO_RANKINGS_SCHEMA.validate(df)


# ---------------------------------------------------------------------------
# seo_traffic  (APE-84 / APE-18b)
# ---------------------------------------------------------------------------

SEO_TRAFFIC_SCHEMA = DataFrameSchema(
    {
        "id":               Column(str, nullable=False),
        "week_start":       Column("object", nullable=False),
        "product_category": Column(str, Check.isin(SEO_CATEGORIES), nullable=False),
        "organic_sessions": Column(int, Check.in_range(5_000, 50_000), nullable=False),
        "organic_accounts": Column(int, Check.in_range(50, 500), nullable=False),
        "bounce_rate":      Column(float, Check.in_range(0.30, 0.65), nullable=False),
    },
    checks=[
        Check(lambda df: len(df) == 72,
              error="seo_traffic: expected 72 rows (6 categories × 12 weeks)"),
        Check(lambda df: df["product_category"].nunique() == 6,
              error="seo_traffic: expected 6 product categories"),
        Check(lambda df: df["week_start"].nunique() == 12,
              error="seo_traffic: expected 12 weeks"),
    ],
    coerce=True,
)


def validate_seo_traffic(df: pd.DataFrame) -> pd.DataFrame:
    """Validate seo_traffic DataFrame."""
    return SEO_TRAFFIC_SCHEMA.validate(df)


# ---------------------------------------------------------------------------
# seo_keyword_rankings  (APE-102)
# ---------------------------------------------------------------------------

SEO_PRODUCTS_102 = [
    "checking", "savings", "mortgage", "auto_loan",
    "credit_card", "personal_loan", "wealth_mgmt",
]

SEO_KEYWORD_RANKINGS_SCHEMA = DataFrameSchema(
    {
        "id":                    Column(str, nullable=False),
        "keyword":               Column(str, nullable=False),
        "product_category":      Column(str, Check.isin(SEO_PRODUCTS_102), nullable=False),
        "current_rank":          Column(int, Check.in_range(1, 200), nullable=False),
        "page_num":              Column(int, Check.isin([1, 2, 3]), nullable=False),
        "prev_month_rank":       Column(int, Check.in_range(1, 200), nullable=False),
        "rank_change":           Column(int, nullable=False),
        "monthly_search_volume": Column(int, Check.greater_than(0), nullable=False),
        "difficulty_score":      Column(int, Check.in_range(1, 100), nullable=False),
        "record_month":          Column("object", nullable=False),
    },
    checks=[
        Check(lambda df: len(df) >= 500, error="seo_keyword_rankings: must have >= 500 rows"),
        Check(lambda df: df["product_category"].nunique() == 7, error="seo_keyword_rankings: must have 7 product categories"),
        Check(
            lambda df: abs(df[df["page_num"] == 1].shape[0] / len(df) - 0.30) < 0.06,
            error="seo_keyword_rankings: page 1 share must be ~30% (±6%)",
        ),
        Check(
            lambda df: abs(df[df["page_num"] == 2].shape[0] / len(df) - 0.25) < 0.06,
            error="seo_keyword_rankings: page 2 share must be ~25% (±6%)",
        ),
        Check(
            lambda df: (df[df["page_num"] == 1]["current_rank"] <= 10).all(),
            error="seo_keyword_rankings: page 1 keywords must have rank <= 10",
        ),
        Check(
            lambda df: (df[df["page_num"] == 2]["current_rank"].between(11, 20)).all(),
            error="seo_keyword_rankings: page 2 keywords must have rank 11–20",
        ),
    ],
    coerce=True,
)


def validate_seo_keyword_rankings(df: pd.DataFrame) -> pd.DataFrame:
    """Validate seo_keyword_rankings DataFrame."""
    return SEO_KEYWORD_RANKINGS_SCHEMA.validate(df)


# ---------------------------------------------------------------------------
# seo_organic_traffic  (APE-102)
# ---------------------------------------------------------------------------

SEO_ORGANIC_TRAFFIC_SCHEMA = DataFrameSchema(
    {
        "id":                  Column(str, nullable=False),
        "month":               Column("object", nullable=False),
        "product_category":    Column(str, Check.isin(SEO_PRODUCTS_102), nullable=False),
        "sessions":            Column(int, Check.greater_than(0), nullable=False),
        "organic_conversions": Column(int, Check.greater_than_or_equal_to(0), nullable=False),
        "conversion_rate":     Column(float, Check.in_range(0.0, 0.20), nullable=False),
        "mom_growth_pct":      Column(float, nullable=False),
    },
    checks=[
        Check(lambda df: len(df) == 84, error="seo_organic_traffic: expected 84 rows (7 products × 12 months)"),
        Check(lambda df: df["product_category"].nunique() == 7, error="seo_organic_traffic: must have 7 product categories"),
        Check(lambda df: df["month"].nunique() == 12, error="seo_organic_traffic: must have 12 distinct months"),
        Check(
            lambda df: (
                df.groupby("month")["sessions"].sum().iloc[-1]
                > df.groupby("month")["sessions"].sum().iloc[0]
            ),
            error="seo_organic_traffic: total sessions must grow from first to last month",
        ),
        Check(
            lambda df: df.groupby("month")["sessions"].sum().mean() > 100_000,
            error="seo_organic_traffic: average monthly sessions must exceed 100,000",
        ),
    ],
    coerce=True,
)


def validate_seo_organic_traffic(df: pd.DataFrame) -> pd.DataFrame:
    """Validate seo_organic_traffic DataFrame."""
    return SEO_ORGANIC_TRAFFIC_SCHEMA.validate(df)


# ---------------------------------------------------------------------------
# seo_technical_metrics  (APE-102)
# ---------------------------------------------------------------------------

SEO_TECHNICAL_METRICS_SCHEMA = DataFrameSchema(
    {
        "id":                    Column(str, nullable=False),
        "page_group":            Column(str, Check.isin(SEO_PRODUCTS_102), nullable=False),
        "lcp_ms":                Column(float, Check.in_range(500, 8_000), nullable=False),
        "fid_ms":                Column(float, Check.in_range(10, 500), nullable=False),
        "cls_score":             Column(float, Check.in_range(0.0, 0.40), nullable=False),
        "pages_indexed":         Column(int, Check.greater_than(0), nullable=False),
        "pages_submitted":       Column(int, Check.greater_than(0), nullable=False),
        "index_coverage_pct":    Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "crawl_budget_used_pct": Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "record_date":           Column("object", nullable=False),
    },
    checks=[
        Check(lambda df: len(df) == 7, error="seo_technical_metrics: expected 7 rows (one per page group)"),
        Check(lambda df: df["page_group"].nunique() == 7, error="seo_technical_metrics: all 7 page groups must be present"),
        Check(
            lambda df: (df["pages_indexed"] <= df["pages_submitted"]).all(),
            error="seo_technical_metrics: pages_indexed must not exceed pages_submitted",
        ),
    ],
    coerce=True,
)


def validate_seo_technical_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Validate seo_technical_metrics DataFrame."""
    return SEO_TECHNICAL_METRICS_SCHEMA.validate(df)


# ---------------------------------------------------------------------------
# Cross-channel budget reconciliation  (APE-103)
# ---------------------------------------------------------------------------

_TOTAL_MEDIA_BUDGET = 15_000_000.0

# Expected % allocation per channel; must sum to 1.0
_EXPECTED_CHANNEL_PCTS: dict[str, float] = {
    "sem":             0.25,
    "social_paid":     0.15,
    "brand_media":     0.40,
    "life_events":     0.12,
    "seo_aeo":         0.05,
    "testing_reserve": 0.03,
}

# Per-channel spend tolerance (±$) — brand_media has float accumulation noise
_CHANNEL_SPEND_TOLERANCE: dict[str, float] = {
    "sem":             1.0,
    "social_paid":     1.0,
    "brand_media":    10.0,
    "life_events":     1.0,
    "seo_aeo":         1.0,
    "testing_reserve": 1.0,
}

CHANNEL_BUDGET_RECONCILIATION_SCHEMA = DataFrameSchema(
    {
        "channel": Column(str, Check.isin(list(_EXPECTED_CHANNEL_PCTS.keys())), nullable=False),
        "pct":     Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "spend":   Column(float, Check.greater_than_or_equal_to(0), nullable=False),
    },
    checks=[
        Check(
            lambda df: len(df) == len(_EXPECTED_CHANNEL_PCTS),
            error=f"channel_budget_reconciliation: expected {len(_EXPECTED_CHANNEL_PCTS)} channel rows",
        ),
        Check(
            lambda df: abs(df["pct"].sum() - 1.0) < 1e-9,
            error="channel_budget_reconciliation: pct column must sum to exactly 1.0",
        ),
        Check(
            lambda df: abs(df["spend"].sum() - _TOTAL_MEDIA_BUDGET) < 15.0,
            error=(
                f"channel_budget_reconciliation: total spend "
                f"${_TOTAL_MEDIA_BUDGET:,.0f} expected (±$15 combined tolerance)"
            ),
        ),
    ],
    coerce=True,
)


def validate_channel_budget_reconciliation(
    df: pd.DataFrame,
    total_media_budget: float = _TOTAL_MEDIA_BUDGET,
) -> pd.DataFrame:
    """Validate the cross-channel budget reconciliation DataFrame.

    Expected columns: channel, pct, spend
    Checks:
      - All 6 channels present with correct pct values
      - Each channel's spend matches expected_pct × total_media_budget within tolerance
      - Total spend = total_media_budget (±$15 combined)

    Args:
        df: One row per channel with columns [channel, pct, spend].
        total_media_budget: Total annual media budget (default $15,000,000).

    Returns validated df or raises SchemaError / ValueError.
    """
    validated = CHANNEL_BUDGET_RECONCILIATION_SCHEMA.validate(df)

    # Per-channel spend vs expected allocation
    errors: list[str] = []
    for _, row in validated.iterrows():
        channel = str(row["channel"])
        spend   = float(row["spend"])
        expected_pct  = _EXPECTED_CHANNEL_PCTS.get(channel, 0.0)
        expected_spend = total_media_budget * expected_pct
        tolerance      = _CHANNEL_SPEND_TOLERANCE.get(channel, 1.0)
        if abs(spend - expected_spend) > tolerance:
            errors.append(
                f"  {channel}: spend ${spend:,.2f} vs expected "
                f"${expected_spend:,.2f} (diff ${abs(spend - expected_spend):,.2f} > ±${tolerance:.0f})"
            )
    if errors:
        raise ValueError(
            "channel_budget_reconciliation: per-channel spend deviations:\n"
            + "\n".join(errors)
        )

    return validated
