"""
Metric definitions — the single source of truth for every KPI in Apex.

Each MetricDefinition contains:
  - name / display_label / description
  - format_type (currency, percent, number, index)
  - grain (daily, weekly, monthly, snapshot)
  - direction (higher_better, lower_better)
  - SQL expression or Python callable for computation
  - thresholds for alert coloring
  - domain ownership (scorecard, spend, channels, funnel, retention, product)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MetricFormat(str, Enum):
    CURRENCY = "currency"
    PERCENT = "percent"
    NUMBER = "number"
    INDEX = "index"
    RATIO = "ratio"
    DURATION = "duration"


class MetricGrain(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SNAPSHOT = "snapshot"


class MetricDirection(str, Enum):
    HIGHER_BETTER = "higher_better"
    LOWER_BETTER = "lower_better"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class Threshold:
    """Alert thresholds for a metric."""
    warning_low: Optional[float] = None
    warning_high: Optional[float] = None
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None


@dataclass(frozen=True)
class MetricDefinition:
    """Immutable definition of a KPI."""
    id: str                                # e.g. "roas"
    display_label: str                     # e.g. "ROAS"
    description: str                       # e.g. "Return on Ad Spend"
    format_type: MetricFormat = MetricFormat.NUMBER
    grain: MetricGrain = MetricGrain.MONTHLY
    direction: MetricDirection = MetricDirection.HIGHER_BETTER
    domain: str = "scorecard"              # owning domain
    unit: str = ""                         # e.g. "$", "%", "days"
    decimal_places: int = 1
    sql_expression: str = ""               # SQL fragment for DB computation
    threshold: Threshold = field(default_factory=Threshold)
    tags: tuple[str, ...] = ()             # grouping tags ("executive", "media", "efficiency")
    sparkline_enabled: bool = True
    target_field: str = ""                 # name of the corresponding target/benchmark column


# ─── Standard Metric Catalog ──────────────────────────────────────────

METRIC_CATALOG: dict[str, MetricDefinition] = {}


def _register(m: MetricDefinition) -> MetricDefinition:
    METRIC_CATALOG[m.id] = m
    return m


# ── Executive / Scorecard ────────────────────────────────────────────

_register(MetricDefinition(
    id="total_spend",
    display_label="Total Spend",
    description="Total marketing spend across all channels",
    format_type=MetricFormat.CURRENCY,
    grain=MetricGrain.MONTHLY,
    direction=MetricDirection.NEUTRAL,
    domain="scorecard",
    unit="$",
    decimal_places=0,
    sql_expression="SUM(spend)",
    tags=("executive", "spend"),
))

_register(MetricDefinition(
    id="funded_accounts",
    display_label="Funded Accounts",
    description="Total new funded household accounts",
    format_type=MetricFormat.NUMBER,
    grain=MetricGrain.MONTHLY,
    direction=MetricDirection.HIGHER_BETTER,
    domain="scorecard",
    decimal_places=0,
    sql_expression="SUM(funded_accounts)",
    tags=("executive", "funnel"),
))

_register(MetricDefinition(
    id="roas",
    display_label="ROAS",
    description="Return on Ad Spend — attributed revenue / total spend",
    format_type=MetricFormat.RATIO,
    grain=MetricGrain.MONTHLY,
    direction=MetricDirection.HIGHER_BETTER,
    domain="scorecard",
    unit="x",
    decimal_places=2,
    sql_expression="SUM(attributed_revenue) / NULLIF(SUM(spend), 0)",
    threshold=Threshold(warning_low=2.0, critical_low=1.0),
    tags=("executive", "efficiency"),
))

_register(MetricDefinition(
    id="cpl",
    display_label="CPL",
    description="Cost per Lead",
    format_type=MetricFormat.CURRENCY,
    grain=MetricGrain.MONTHLY,
    direction=MetricDirection.LOWER_BETTER,
    domain="scorecard",
    unit="$",
    decimal_places=0,
    sql_expression="SUM(spend) / NULLIF(SUM(leads), 0)",
    threshold=Threshold(warning_high=120, critical_high=180),
    tags=("executive", "efficiency"),
))

_register(MetricDefinition(
    id="cpihh",
    display_label="CPIHH",
    description="Cost per Incremental Household — spend per funded account",
    format_type=MetricFormat.CURRENCY,
    grain=MetricGrain.MONTHLY,
    direction=MetricDirection.LOWER_BETTER,
    domain="scorecard",
    unit="$",
    decimal_places=0,
    sql_expression="SUM(spend) / NULLIF(SUM(funded_accounts), 0)",
    threshold=Threshold(warning_high=300, critical_high=450),
    tags=("executive", "efficiency"),
))

_register(MetricDefinition(
    id="cpm",
    display_label="CPM",
    description="Cost per Mille — cost per 1,000 impressions",
    format_type=MetricFormat.CURRENCY,
    grain=MetricGrain.MONTHLY,
    direction=MetricDirection.LOWER_BETTER,
    domain="channels",
    unit="$",
    decimal_places=2,
    sql_expression="(SUM(spend) / NULLIF(SUM(impressions), 0)) * 1000",
    tags=("media",),
))

_register(MetricDefinition(
    id="ctr",
    display_label="CTR",
    description="Click-Through Rate",
    format_type=MetricFormat.PERCENT,
    grain=MetricGrain.MONTHLY,
    direction=MetricDirection.HIGHER_BETTER,
    domain="channels",
    unit="%",
    decimal_places=2,
    sql_expression="SUM(clicks) / NULLIF(SUM(impressions), 0)",
    tags=("media",),
))

_register(MetricDefinition(
    id="cvr",
    display_label="CVR",
    description="Conversion Rate — funded / clicks",
    format_type=MetricFormat.PERCENT,
    grain=MetricGrain.MONTHLY,
    direction=MetricDirection.HIGHER_BETTER,
    domain="channels",
    unit="%",
    decimal_places=2,
    sql_expression="SUM(conversions) / NULLIF(SUM(clicks), 0)",
    tags=("media", "funnel"),
))

_register(MetricDefinition(
    id="quality_score",
    display_label="Quality Score",
    description="Google Ads quality score (1–10)",
    format_type=MetricFormat.NUMBER,
    grain=MetricGrain.WEEKLY,
    direction=MetricDirection.HIGHER_BETTER,
    domain="channels",
    decimal_places=1,
    sql_expression="AVG(quality_score)",
    threshold=Threshold(warning_low=5, critical_low=3),
    tags=("sem",),
))

# ── BEI / LLM Visibility ────────────────────────────────────────────

_register(MetricDefinition(
    id="bei",
    display_label="BEI",
    description="Brand Equity Index — composite brand health score",
    format_type=MetricFormat.INDEX,
    grain=MetricGrain.MONTHLY,
    direction=MetricDirection.HIGHER_BETTER,
    domain="channels",
    decimal_places=1,
    sql_expression="AVG(bei_score)",
    threshold=Threshold(warning_low=60, critical_low=45),
    tags=("brand", "executive"),
))

_register(MetricDefinition(
    id="llm_visibility",
    display_label="LLM Visibility",
    description="AI/LLM answer-engine visibility score — share of AI-generated answers mentioning brand",
    format_type=MetricFormat.PERCENT,
    grain=MetricGrain.MONTHLY,
    direction=MetricDirection.HIGHER_BETTER,
    domain="channels",
    unit="%",
    decimal_places=1,
    sql_expression="AVG(visibility_score)",
    threshold=Threshold(warning_low=0.15, critical_low=0.05),
    tags=("aeo", "brand"),
))

_register(MetricDefinition(
    id="share_of_search",
    display_label="Share of Search",
    description="Brand search volume as % of category",
    format_type=MetricFormat.PERCENT,
    grain=MetricGrain.MONTHLY,
    direction=MetricDirection.HIGHER_BETTER,
    domain="channels",
    unit="%",
    decimal_places=1,
    sql_expression="SUM(brand_msv) / NULLIF(SUM(total_msv), 0)",
    tags=("brand",),
))

# ── Funnel ───────────────────────────────────────────────────────────

_register(MetricDefinition(
    id="visit_to_app_rate",
    display_label="Visit→App Rate",
    description="Percentage of site visits that start an application",
    format_type=MetricFormat.PERCENT,
    grain=MetricGrain.MONTHLY,
    direction=MetricDirection.HIGHER_BETTER,
    domain="funnel",
    unit="%",
    decimal_places=1,
    sql_expression="SUM(app_starts) / NULLIF(SUM(visits), 0)",
    tags=("funnel",),
))

_register(MetricDefinition(
    id="app_to_fund_rate",
    display_label="App→Fund Rate",
    description="Percentage of applications that result in funded accounts",
    format_type=MetricFormat.PERCENT,
    grain=MetricGrain.MONTHLY,
    direction=MetricDirection.HIGHER_BETTER,
    domain="funnel",
    unit="%",
    decimal_places=1,
    sql_expression="SUM(funded) / NULLIF(SUM(applications), 0)",
    tags=("funnel",),
))

_register(MetricDefinition(
    id="funded_per_media_dollar",
    display_label="Funded/Media $",
    description="Funded accounts per media dollar spent",
    format_type=MetricFormat.RATIO,
    grain=MetricGrain.MONTHLY,
    direction=MetricDirection.HIGHER_BETTER,
    domain="funnel",
    decimal_places=4,
    sql_expression="SUM(funded_accounts) / NULLIF(SUM(spend), 0)",
    tags=("efficiency", "funnel"),
))

# ── Retention ────────────────────────────────────────────────────────

_register(MetricDefinition(
    id="mob6_retention",
    display_label="MOB-6 Retention",
    description="Retention rate at 6 months on books",
    format_type=MetricFormat.PERCENT,
    grain=MetricGrain.MONTHLY,
    direction=MetricDirection.HIGHER_BETTER,
    domain="retention",
    unit="%",
    decimal_places=1,
    sql_expression="AVG(mob6_rate)",
    threshold=Threshold(warning_low=0.70, critical_low=0.60),
    tags=("retention", "executive"),
))

_register(MetricDefinition(
    id="churn_90d",
    display_label="90-Day Churn",
    description="Account churn rate within first 90 days",
    format_type=MetricFormat.PERCENT,
    grain=MetricGrain.MONTHLY,
    direction=MetricDirection.LOWER_BETTER,
    domain="retention",
    unit="%",
    decimal_places=1,
    sql_expression="AVG(churn_90d)",
    threshold=Threshold(warning_high=0.10, critical_high=0.15),
    tags=("retention",),
))

_register(MetricDefinition(
    id="portfolio_ltv",
    display_label="Portfolio LTV",
    description="Estimated lifetime value of the active portfolio",
    format_type=MetricFormat.CURRENCY,
    grain=MetricGrain.QUARTERLY,
    direction=MetricDirection.HIGHER_BETTER,
    domain="retention",
    unit="$",
    decimal_places=0,
    sql_expression="SUM(ltv_estimate)",
    tags=("retention", "executive"),
))

# ── Spend & Allocation ──────────────────────────────────────────────

_register(MetricDefinition(
    id="budget_utilization",
    display_label="Budget Utilization",
    description="Percentage of allocated budget actually spent",
    format_type=MetricFormat.PERCENT,
    grain=MetricGrain.MONTHLY,
    direction=MetricDirection.NEUTRAL,
    domain="spend",
    unit="%",
    decimal_places=1,
    sql_expression="SUM(actual_spend) / NULLIF(SUM(planned_spend), 0)",
    tags=("spend",),
))

_register(MetricDefinition(
    id="waste_gap",
    display_label="Waste Gap",
    description="Annual $ left on the table from suboptimal allocation",
    format_type=MetricFormat.CURRENCY,
    grain=MetricGrain.SNAPSHOT,
    direction=MetricDirection.LOWER_BETTER,
    domain="spend",
    unit="$",
    decimal_places=0,
    tags=("spend", "optimization"),
))

_register(MetricDefinition(
    id="marginal_roas",
    display_label="Marginal ROAS",
    description="ROAS on the next marginal dollar of spend",
    format_type=MetricFormat.RATIO,
    grain=MetricGrain.SNAPSHOT,
    direction=MetricDirection.HIGHER_BETTER,
    domain="spend",
    unit="x",
    decimal_places=2,
    tags=("spend", "optimization"),
))

# ── Product & Ops ────────────────────────────────────────────────────

_register(MetricDefinition(
    id="testing_win_rate",
    display_label="Test Win Rate",
    description="Percentage of A/B tests that produce a statistically significant winner",
    format_type=MetricFormat.PERCENT,
    grain=MetricGrain.MONTHLY,
    direction=MetricDirection.HIGHER_BETTER,
    domain="product",
    unit="%",
    decimal_places=1,
    tags=("product", "experiments"),
))

_register(MetricDefinition(
    id="avg_test_lift",
    display_label="Avg Test Lift",
    description="Average lift percentage from winning A/B tests",
    format_type=MetricFormat.PERCENT,
    grain=MetricGrain.MONTHLY,
    direction=MetricDirection.HIGHER_BETTER,
    domain="product",
    unit="%",
    decimal_places=1,
    tags=("product", "experiments"),
))

_register(MetricDefinition(
    id="approval_queue_depth",
    display_label="Queue Depth",
    description="Number of pending items in the approval queue",
    format_type=MetricFormat.NUMBER,
    grain=MetricGrain.SNAPSHOT,
    direction=MetricDirection.LOWER_BETTER,
    domain="product",
    decimal_places=0,
    tags=("ops",),
))

_register(MetricDefinition(
    id="compliance_score",
    display_label="Compliance Score",
    description="Average compliance pass rate across audited pages",
    format_type=MetricFormat.PERCENT,
    grain=MetricGrain.SNAPSHOT,
    direction=MetricDirection.HIGHER_BETTER,
    domain="product",
    unit="%",
    decimal_places=0,
    threshold=Threshold(warning_low=0.85, critical_low=0.70),
    tags=("audit", "compliance"),
))
