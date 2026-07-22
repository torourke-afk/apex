"""
Seed Connector
==============

Wraps the existing DuckDB + in-memory seed data layer as a connector.
This is the default fallback — always available, never needs credentials.

It delegates to the same query functions the BFF routers currently call
directly, so behaviour is identical to the pre-connector architecture.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from .base import (
    BaseConnector,
    ConnectorConfig,
    ConnectorHealth,
    DataDomain,
    QueryFilters,
)

logger = logging.getLogger(__name__)


def _default_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_type="seed",
        display_name="Built-in Seed Data",
        domains=list(DataDomain),          # serves every domain as fallback
        enabled=True,
        refresh_interval_minutes=0,        # no refresh — data is static
    )


class SeedConnector(BaseConnector):
    """Connector that wraps the existing seed / DuckDB data layer."""

    def __init__(self, config: ConnectorConfig | None = None) -> None:
        super().__init__(config or _default_config())

    # -- Lifecycle ----------------------------------------------------------

    async def connect(self) -> bool:
        self._health = ConnectorHealth(
            status="connected",
            last_sync=datetime.utcnow(),
            rows_synced=0,
            details={"note": "Seed data — no external connection required"},
        )
        return True

    async def disconnect(self) -> None:
        self._health = ConnectorHealth(status="disconnected")

    async def health_check(self) -> ConnectorHealth:
        # Seed is always healthy if connected
        if self._health.status == "connected":
            self._health.latency_ms = 0.0
        return self._health

    # -- Data fetching ------------------------------------------------------

    async def fetch(
        self,
        domain: DataDomain,
        endpoint: str,
        filters: QueryFilters | None = None,
    ) -> Any:
        """Dispatch to the matching seed data function."""
        handler_key = f"{domain.value}.{endpoint}"
        handler = _DISPATCH.get(handler_key)

        if handler is None:
            logger.warning("SeedConnector: no handler for %s", handler_key)
            return None

        try:
            return handler(filters)
        except Exception as exc:
            logger.error("SeedConnector fetch error (%s): %s", handler_key, exc)
            return None


# ---------------------------------------------------------------------------
# Dispatch table — maps domain.endpoint to a callable
# ---------------------------------------------------------------------------

def _spend_overview(f: QueryFilters | None) -> Any:
    from src.data.spend_queries import get_budget_overview
    return get_budget_overview(f.to_dict() if f else None)


def _spend_pacing(f: QueryFilters | None) -> Any:
    from src.data.spend_queries import get_channel_spend_breakdown
    return get_channel_spend_breakdown(f.to_dict() if f else None)


def _spend_dma(f: QueryFilters | None) -> Any:
    from src.data.spend_queries import get_market_allocation
    return get_market_allocation(f.to_dict() if f else None)


def _funnel_stages(f: QueryFilters | None) -> Any:
    from src.data.funnel_queries import get_funnel_stages
    return get_funnel_stages(f.to_dict() if f else None)


def _funnel_dropoff(f: QueryFilters | None) -> Any:
    from src.data.funnel_queries import get_dropoff_analysis
    return get_dropoff_analysis(filters=f.to_dict() if f else None)


def _scorecard_kpis(f: QueryFilters | None) -> Any:
    from src.data.scorecard_queries import get_kpi_summary
    return get_kpi_summary()


def _scorecard_financial(f: QueryFilters | None) -> Any:
    from src.data.scorecard_queries import get_financial_summary
    return get_financial_summary()


def _scorecard_alerts(f: QueryFilters | None) -> Any:
    from src.data.scorecard_queries import get_recent_alerts
    return get_recent_alerts()


def _sem_overview(f: QueryFilters | None) -> Any:
    from src.data.sem_queries import get_sem_overview
    return get_sem_overview()


def _brand_awareness_sos(f: QueryFilters | None) -> Any:
    from src.data.brand_awareness import BrandTracker, BrandTrackerConfig, FITB_PRESET
    config = BrandTrackerConfig(
        brand_name=FITB_PRESET["brand"],
        brand_keyword=FITB_PRESET["brand_keyword"],
        brand_domain=FITB_PRESET["domain"],
        competitors=FITB_PRESET["competitors"],
    )
    tracker = BrandTracker(config)
    geo = f.extra.get("geo", "national") if f else "national"
    return tracker.get_share_of_search(geo=geo)


def _retention_curves(f: QueryFilters | None) -> Any:
    from src.data.retention_forecast import get_survival_curves
    return get_survival_curves()


def _product_pipeline(f: QueryFilters | None) -> Any:
    from src.data.product_queries import get_pipeline
    return get_pipeline()


def _product_testing(f: QueryFilters | None) -> Any:
    from src.data.product_queries import get_testing_velocity
    return get_testing_velocity()


def _ops_approvals(f: QueryFilters | None) -> Any:
    # Approvals are ORM-based — handled directly in the router
    return None


def _ops_calendar(f: QueryFilters | None) -> Any:
    from src.data.ops_queries import get_calendar
    return get_calendar()


def _social_overview(f: QueryFilters | None) -> Any:
    from src.data.load_social import load_social_data
    return load_social_data()


def _brand_media_overview(f: QueryFilters | None) -> Any:
    from src.data.social_brand_loaders import load_brand_media_summary
    return load_brand_media_summary()


def _seo_rankings(f: QueryFilters | None) -> Any:
    from src.data.organic_loaders import load_seo_rankings
    return load_seo_rankings()


def _aeo_summary(f: QueryFilters | None) -> Any:
    from src.data.organic_aeo import get_aeo_summary
    return get_aeo_summary()


# The dispatch table
_DISPATCH: dict[str, Any] = {
    # Spend
    "spend.overview": _spend_overview,
    "spend.pacing": _spend_pacing,
    "spend.dma": _spend_dma,
    # Funnel
    "funnel.stages": _funnel_stages,
    "funnel.dropoff": _funnel_dropoff,
    # Scorecard
    "scorecard.kpis": _scorecard_kpis,
    "scorecard.financial": _scorecard_financial,
    "scorecard.alerts": _scorecard_alerts,
    # SEM
    "sem.overview": _sem_overview,
    # Brand Awareness
    "brand_awareness.share_of_search": _brand_awareness_sos,
    # Retention
    "retention.curves": _retention_curves,
    # Product
    "product.pipeline": _product_pipeline,
    "product.testing": _product_testing,
    # Ops
    "ops.approvals": _ops_approvals,
    "ops.calendar": _ops_calendar,
    # Social
    "social.overview": _social_overview,
    # Brand Media
    "brand_media.overview": _brand_media_overview,
    # SEO
    "seo.rankings": _seo_rankings,
    # AEO
    "aeo.summary": _aeo_summary,
}
