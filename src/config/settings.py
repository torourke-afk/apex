"""
Apex application settings and configuration.
"""

import os

# ---------------------------------------------------------------------------
# App metadata
# ---------------------------------------------------------------------------

APP_NAME = "Apex"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "RVGT marketing intelligence platform for competitive analysis and campaign performance."

# ---------------------------------------------------------------------------
# Database config
# ---------------------------------------------------------------------------

DB_PATH = os.environ.get("APEX_DB_PATH", "apex_clean.duckdb")
DB_URL = os.environ.get("APEX_DB_URL", None)  # PostgreSQL connection string (prod)
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


APEX_DATA_REFRESH_INTERVAL_MINUTES: int = int(
    os.environ.get("APEX_DATA_REFRESH_INTERVAL_MINUTES", "15")
)
APEX_DATA_REFRESH_INTERVAL_SECONDS: int = APEX_DATA_REFRESH_INTERVAL_MINUTES * 60
APEX_DEBUG_MODE: bool = os.environ.get("APEX_DEBUG_MODE", "").strip() in (
    "1",
    "true",
    "yes",
)


def is_dev_mode() -> bool:
    """Return True when running in local development (no DB_URL set)."""
    return DB_URL is None


# ---------------------------------------------------------------------------
# Page registry
# ---------------------------------------------------------------------------

PAGES = [
    {
        "id": "executive_scorecard",
        "title": "Executive Scorecard",
        "icon": ":material/dashboard:",
        "description": "CMO-level KPI dashboard with executive metrics, financial summary, and live alert feed.",
    },
    {
        "id": "spend_allocation",
        "title": "Spend Allocation",
        "icon": ":material/account_balance_wallet:",
        "description": "Budget distribution across channels, campaigns, and business lines with optimisation signals.",
    },
    {
        "id": "brand_media",
        "title": "Brand Media",
        "icon": ":material/campaign:",
        "description": "Brand awareness campaigns: reach, frequency, impressions by channel, BEI, and life events.",
    },
    {
        "id": "performance_media",
        "title": "Performance Media",
        "icon": ":material/trending_up:",
        "description": "Paid search, paid social, and programmatic performance with CPL, ROAS, and quality score.",
    },
    {
        "id": "seo",
        "title": "SEO",
        "icon": ":material/search:",
        "description": "Organic search rankings, keyword performance, traffic trends, and content gap analysis.",
    },
    {
        "id": "aeo",
        "title": "AEO",
        "icon": ":material/smart_toy:",
        "description": "AI Engine Optimisation: LLM visibility score, mention rates, and competitive benchmarking.",
    },
    {
        "id": "acquisition_funnel",
        "title": "Acquisition Funnel",
        "icon": ":material/filter_alt:",
        "description": "Full acquisition funnel from Brand UOI to Active accounts, segmented by product and DMA.",
    },
    {
        "id": "product_experience",
        "title": "Product & Experience",
        "icon": ":material/rocket_launch:",
        "description": "Digital product metrics: funnel drop-off, feature adoption, and UX conversion signals.",
    },
    {
        "id": "operations_command",
        "title": "Operations Command",
        "icon": ":material/terminal:",
        "description": "Launch calendar, team velocity, approval queue, system health, and competitive intel feed.",
    },
    {
        "id": "retention_forecast",
        "title": "Retention Forecast",
        "icon": ":material/show_chart:",
        "description": "Parametric survival curve modeler with segment filters and draggable observation date.",
    },
    {
        "id": "brand_awareness",
        "title": "Brand Awareness",
        "icon": ":material/visibility:",
        "description": "MSV-based brand awareness tracker — competitive share of search across national and DMA footprint.",
    },
    {
        "id": "settings",
        "title": "Settings",
        "icon": ":material/settings:",
        "description": "Application settings: theme, benchmarks, connectors, and BD/Client mode selection.",
    },
]

# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------

FEATURE_FLAGS: dict[str, bool] = {}
