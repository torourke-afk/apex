"""
Google Ads Connector
====================

Pulls campaign performance, keyword data, and ad group metrics
from Google Ads API.  Maps to: spend, sem, brand_awareness domains.

Required credentials (env vars):
    GOOGLE_ADS_DEVELOPER_TOKEN  — developer token
    GOOGLE_ADS_CLIENT_ID        — OAuth client ID
    GOOGLE_ADS_CLIENT_SECRET    — OAuth client secret
    GOOGLE_ADS_REFRESH_TOKEN    — OAuth refresh token
    GOOGLE_ADS_CUSTOMER_ID      — customer account ID (no dashes)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any

from .base import (
    BaseConnector,
    ConnectorConfig,
    ConnectorHealth,
    DataDomain,
    QueryFilters,
)

logger = logging.getLogger(__name__)

_DEFAULT_DEV_TOKEN = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", "")
_DEFAULT_CLIENT_ID = os.environ.get("GOOGLE_ADS_CLIENT_ID", "")
_DEFAULT_CLIENT_SECRET = os.environ.get("GOOGLE_ADS_CLIENT_SECRET", "")
_DEFAULT_REFRESH_TOKEN = os.environ.get("GOOGLE_ADS_REFRESH_TOKEN", "")
_DEFAULT_CUSTOMER_ID = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "")


def default_config() -> ConnectorConfig:
    has_creds = all([_DEFAULT_DEV_TOKEN, _DEFAULT_CLIENT_ID, _DEFAULT_CUSTOMER_ID])
    return ConnectorConfig(
        connector_type="google_ads",
        display_name="Google Ads",
        domains=[DataDomain.SPEND, DataDomain.SEM, DataDomain.BRAND_AWARENESS],
        credentials={
            "developer_token": _DEFAULT_DEV_TOKEN,
            "client_id": _DEFAULT_CLIENT_ID,
            "client_secret": _DEFAULT_CLIENT_SECRET,
            "refresh_token": _DEFAULT_REFRESH_TOKEN,
            "customer_id": _DEFAULT_CUSTOMER_ID,
        },
        settings={
            "include_drafts": False,
            "date_range_days": 90,
        },
        enabled=has_creds,
        refresh_interval_minutes=30,
    )


class GoogleAdsConnector(BaseConnector):
    """Connector for Google Ads API."""

    def __init__(self, config: ConnectorConfig | None = None) -> None:
        super().__init__(config or default_config())
        self._client: Any = None

    # -- Lifecycle ----------------------------------------------------------

    async def connect(self) -> bool:
        dev_token = self.config.credentials.get("developer_token")
        customer_id = self.config.credentials.get("customer_id")

        if not dev_token or not customer_id:
            self._health = ConnectorHealth(
                status="disconnected",
                last_error="Missing Google Ads credentials",
            )
            return False

        try:
            from google.ads.googleads.client import GoogleAdsClient

            creds_dict = {
                "developer_token": dev_token,
                "client_id": self.config.credentials.get("client_id"),
                "client_secret": self.config.credentials.get("client_secret"),
                "refresh_token": self.config.credentials.get("refresh_token"),
                "use_proto_plus": True,
            }
            self._client = GoogleAdsClient.load_from_dict(creds_dict)

            # Validate by fetching accessible customers
            customer_service = self._client.get_service("CustomerService")
            customer_service.list_accessible_customers()

            self._health = ConnectorHealth(
                status="connected",
                last_sync=datetime.utcnow(),
                details={"customer_id": customer_id},
            )
            return True

        except ImportError:
            self._health = ConnectorHealth(
                status="error",
                last_error=(
                    "google-ads package not installed. "
                    "Run: pip install google-ads"
                ),
            )
            return False
        except Exception as exc:
            self._health = ConnectorHealth(
                status="error",
                last_error=str(exc),
            )
            return False

    async def disconnect(self) -> None:
        self._client = None
        self._health = ConnectorHealth(status="disconnected")

    async def health_check(self) -> ConnectorHealth:
        if self._client is None:
            return ConnectorHealth(status="disconnected")
        return self._health

    # -- Data fetching ------------------------------------------------------

    async def fetch(
        self,
        domain: DataDomain,
        endpoint: str,
        filters: QueryFilters | None = None,
    ) -> Any:
        if self._client is None:
            return None

        customer_id = self.config.credentials["customer_id"]

        dispatch = {
            ("spend", "overview"): self._fetch_campaign_spend,
            ("spend", "dma"): self._fetch_geo_performance,
            ("sem", "keywords"): self._fetch_keyword_performance,
            ("sem", "overview"): self._fetch_campaign_metrics,
            ("brand_awareness", "share_of_search"): self._fetch_keyword_planner_msv,
        }

        handler = dispatch.get((domain.value, endpoint))
        if handler is None:
            logger.warning("GoogleAds: no handler for %s.%s", domain.value, endpoint)
            return None

        try:
            result = await handler(customer_id, filters)
            self._health.last_sync = datetime.utcnow()
            return result
        except Exception as exc:
            logger.error("GoogleAds fetch error (%s.%s): %s", domain.value, endpoint, exc)
            self._health.last_error = str(exc)
            self._health.status = "degraded"
            return None

    # -- Google Ads GAQL implementations ------------------------------------

    async def _fetch_campaign_spend(
        self,
        customer_id: str,
        filters: QueryFilters | None,
    ) -> list[dict]:
        """Fetch campaign-level spend data."""
        date_start = filters.date_start if filters else None
        date_end = filters.date_end if filters else None
        if not date_start:
            date_start = (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%d")
        if not date_end:
            date_end = datetime.utcnow().strftime("%Y-%m-%d")

        gaql = f"""
            SELECT
                campaign.name,
                campaign.advertising_channel_type,
                metrics.cost_micros,
                metrics.impressions,
                metrics.clicks,
                metrics.conversions,
                metrics.conversions_value,
                segments.date
            FROM campaign
            WHERE segments.date BETWEEN '{date_start}' AND '{date_end}'
              AND campaign.status = 'ENABLED'
            ORDER BY metrics.cost_micros DESC
        """
        return self._run_gaql(customer_id, gaql)

    async def _fetch_geo_performance(
        self,
        customer_id: str,
        filters: QueryFilters | None,
    ) -> list[dict]:
        """Fetch geo (DMA) level performance."""
        date_start = filters.date_start if filters else None
        date_end = filters.date_end if filters else None
        if not date_start:
            date_start = (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%d")
        if not date_end:
            date_end = datetime.utcnow().strftime("%Y-%m-%d")

        gaql = f"""
            SELECT
                geographic_view.country_criterion_id,
                geographic_view.location_type,
                metrics.cost_micros,
                metrics.impressions,
                metrics.clicks,
                metrics.conversions
            FROM geographic_view
            WHERE segments.date BETWEEN '{date_start}' AND '{date_end}'
            ORDER BY metrics.cost_micros DESC
            LIMIT 50
        """
        return self._run_gaql(customer_id, gaql)

    async def _fetch_keyword_performance(
        self,
        customer_id: str,
        filters: QueryFilters | None,
    ) -> list[dict]:
        """Fetch keyword-level SEM performance."""
        date_start = filters.date_start if filters else None
        date_end = filters.date_end if filters else None
        if not date_start:
            date_start = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not date_end:
            date_end = datetime.utcnow().strftime("%Y-%m-%d")

        gaql = f"""
            SELECT
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                metrics.cost_micros,
                metrics.impressions,
                metrics.clicks,
                metrics.conversions,
                metrics.average_cpc
            FROM keyword_view
            WHERE segments.date BETWEEN '{date_start}' AND '{date_end}'
            ORDER BY metrics.cost_micros DESC
            LIMIT 200
        """
        return self._run_gaql(customer_id, gaql)

    async def _fetch_campaign_metrics(
        self,
        customer_id: str,
        filters: QueryFilters | None,
    ) -> list[dict]:
        """Fetch campaign-level SEM metrics summary."""
        date_start = filters.date_start if filters else None
        date_end = filters.date_end if filters else None
        if not date_start:
            date_start = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not date_end:
            date_end = datetime.utcnow().strftime("%Y-%m-%d")

        gaql = f"""
            SELECT
                campaign.name,
                metrics.cost_micros,
                metrics.impressions,
                metrics.clicks,
                metrics.conversions,
                metrics.search_impression_share
            FROM campaign
            WHERE segments.date BETWEEN '{date_start}' AND '{date_end}'
              AND campaign.advertising_channel_type = 'SEARCH'
              AND campaign.status = 'ENABLED'
            ORDER BY metrics.cost_micros DESC
        """
        return self._run_gaql(customer_id, gaql)

    async def _fetch_keyword_planner_msv(
        self,
        customer_id: str,
        filters: QueryFilters | None,
    ) -> list[dict]:
        """Use Keyword Planner to get MSV for branded terms."""
        try:
            kp_service = self._client.get_service("KeywordPlanIdeaService")
            keywords = self.config.settings.get("brand_keywords", [
                "fifth third bank",
                "huntington bank",
                "keybank",
                "pnc bank",
            ])

            req = self._client.get_type("GenerateKeywordIdeaRequest")
            req.customer_id = customer_id
            req.keyword_seed.keywords.extend(keywords)
            req.language = "languageConstants/1000"  # English
            req.geo_target_constants.append("geoTargetConstants/2840")  # US

            response = kp_service.generate_keyword_ideas(request=req)

            results = []
            for idea in response.results:
                results.append({
                    "keyword": idea.text,
                    "msv": idea.keyword_idea_metrics.avg_monthly_searches,
                    "competition": idea.keyword_idea_metrics.competition.name,
                })

            return results
        except Exception as exc:
            logger.warning("Keyword Planner MSV failed: %s", exc)
            return []

    # -- Helpers ------------------------------------------------------------

    def _run_gaql(self, customer_id: str, gaql: str) -> list[dict]:
        """Execute a GAQL query and return rows as dicts."""
        ga_service = self._client.get_service("GoogleAdsService")
        response = ga_service.search(customer_id=customer_id, query=gaql)

        rows = []
        for row in response:
            row_dict: dict[str, Any] = {}
            # Walk proto fields and flatten into dict
            for field_name in row._pb.DESCRIPTOR.fields_by_name:
                val = getattr(row, field_name, None)
                if val is not None:
                    if hasattr(val, "_pb"):
                        # Nested proto — flatten one level
                        for sub_field in val._pb.DESCRIPTOR.fields_by_name:
                            sub_val = getattr(val, sub_field, None)
                            if sub_val is not None:
                                row_dict[f"{field_name}.{sub_field}"] = sub_val
                    else:
                        row_dict[field_name] = val
            rows.append(row_dict)

        return rows
