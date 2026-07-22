"""
Meta Ads Connector
==================

Pulls campaign performance from Meta Marketing API (Facebook + Instagram).
Maps to: social, creative domains.

Required credentials (env vars):
    META_ADS_ACCESS_TOKEN  — long-lived user/system access token
    META_ADS_ACCOUNT_ID    — ad account ID (act_XXXXX)
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

_API_VERSION = "v20.0"
_API_BASE = f"https://graph.facebook.com/{_API_VERSION}"
_DEFAULT_TOKEN = os.environ.get("META_ADS_ACCESS_TOKEN", "")
_DEFAULT_ACCOUNT = os.environ.get("META_ADS_ACCOUNT_ID", "")


def default_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_type="meta_ads",
        display_name="Meta Ads (Facebook / Instagram)",
        domains=[DataDomain.SOCIAL, DataDomain.CREATIVE],
        credentials={
            "access_token": _DEFAULT_TOKEN,
            "account_id": _DEFAULT_ACCOUNT,
        },
        settings={
            "breakdowns": ["age", "gender", "publisher_platform"],
            "date_range_days": 90,
        },
        enabled=bool(_DEFAULT_TOKEN and _DEFAULT_ACCOUNT),
        refresh_interval_minutes=30,
    )


class MetaAdsConnector(BaseConnector):
    """Connector for Meta Marketing API."""

    def __init__(self, config: ConnectorConfig | None = None) -> None:
        super().__init__(config or default_config())
        self._session: Any = None

    # -- Lifecycle ----------------------------------------------------------

    async def connect(self) -> bool:
        token = self.config.credentials.get("access_token")
        account_id = self.config.credentials.get("account_id")

        if not token or not account_id:
            self._health = ConnectorHealth(
                status="disconnected",
                last_error="Missing META_ADS_ACCESS_TOKEN or META_ADS_ACCOUNT_ID",
            )
            return False

        try:
            import httpx

            self._session = httpx.AsyncClient(timeout=30.0)

            # Validate token
            resp = await self._session.get(
                f"{_API_BASE}/{account_id}",
                params={"access_token": token, "fields": "name,account_status"},
            )
            data = resp.json()

            if "error" in data:
                self._health = ConnectorHealth(
                    status="error",
                    last_error=data["error"].get("message", "Unknown Meta API error"),
                )
                return False

            self._health = ConnectorHealth(
                status="connected",
                last_sync=datetime.utcnow(),
                details={
                    "account_name": data.get("name", ""),
                    "account_id": account_id,
                },
            )
            return True

        except ImportError:
            self._health = ConnectorHealth(
                status="error",
                last_error="httpx package not installed. Run: pip install httpx",
            )
            return False
        except Exception as exc:
            self._health = ConnectorHealth(
                status="error",
                last_error=str(exc),
            )
            return False

    async def disconnect(self) -> None:
        if self._session:
            await self._session.aclose()
            self._session = None
        self._health = ConnectorHealth(status="disconnected")

    async def health_check(self) -> ConnectorHealth:
        if self._session is None:
            return ConnectorHealth(status="disconnected")
        return self._health

    # -- Data fetching ------------------------------------------------------

    async def fetch(
        self,
        domain: DataDomain,
        endpoint: str,
        filters: QueryFilters | None = None,
    ) -> Any:
        if self._session is None:
            return None

        token = self.config.credentials["access_token"]
        account_id = self.config.credentials["account_id"]

        dispatch = {
            ("social", "overview"): self._fetch_account_insights,
            ("social", "campaigns"): self._fetch_campaign_insights,
            ("social", "platforms"): self._fetch_platform_breakdown,
            ("creative", "performance"): self._fetch_ad_creative_perf,
        }

        handler = dispatch.get((domain.value, endpoint))
        if handler is None:
            logger.warning("MetaAds: no handler for %s.%s", domain.value, endpoint)
            return None

        try:
            result = await handler(token, account_id, filters)
            self._health.last_sync = datetime.utcnow()
            return result
        except Exception as exc:
            logger.error("MetaAds fetch error (%s.%s): %s", domain.value, endpoint, exc)
            self._health.last_error = str(exc)
            self._health.status = "degraded"
            return None

    # -- Meta API implementations -------------------------------------------

    async def _fetch_account_insights(
        self,
        token: str,
        account_id: str,
        filters: QueryFilters | None,
    ) -> dict[str, Any]:
        """Fetch account-level performance insights."""
        date_start, date_end = self._date_range(filters)
        resp = await self._session.get(
            f"{_API_BASE}/{account_id}/insights",
            params={
                "access_token": token,
                "fields": "spend,impressions,clicks,cpc,cpm,ctr,actions,cost_per_action_type",
                "time_range": f'{{"since":"{date_start}","until":"{date_end}"}}',
                "time_increment": 1,
            },
        )
        return resp.json()

    async def _fetch_campaign_insights(
        self,
        token: str,
        account_id: str,
        filters: QueryFilters | None,
    ) -> dict[str, Any]:
        """Fetch campaign-level insights."""
        date_start, date_end = self._date_range(filters)
        resp = await self._session.get(
            f"{_API_BASE}/{account_id}/insights",
            params={
                "access_token": token,
                "fields": "campaign_name,spend,impressions,clicks,cpc,actions",
                "level": "campaign",
                "time_range": f'{{"since":"{date_start}","until":"{date_end}"}}',
                "limit": 100,
            },
        )
        return resp.json()

    async def _fetch_platform_breakdown(
        self,
        token: str,
        account_id: str,
        filters: QueryFilters | None,
    ) -> dict[str, Any]:
        """Fetch insights broken down by publisher platform (FB vs IG)."""
        date_start, date_end = self._date_range(filters)
        resp = await self._session.get(
            f"{_API_BASE}/{account_id}/insights",
            params={
                "access_token": token,
                "fields": "spend,impressions,clicks,actions",
                "breakdowns": "publisher_platform",
                "time_range": f'{{"since":"{date_start}","until":"{date_end}"}}',
            },
        )
        return resp.json()

    async def _fetch_ad_creative_perf(
        self,
        token: str,
        account_id: str,
        filters: QueryFilters | None,
    ) -> dict[str, Any]:
        """Fetch ad-creative-level performance."""
        date_start, date_end = self._date_range(filters)
        resp = await self._session.get(
            f"{_API_BASE}/{account_id}/insights",
            params={
                "access_token": token,
                "fields": "ad_name,spend,impressions,clicks,ctr,cpc,actions",
                "level": "ad",
                "time_range": f'{{"since":"{date_start}","until":"{date_end}"}}',
                "limit": 50,
                "sort": "spend_descending",
            },
        )
        return resp.json()

    # -- Helpers ------------------------------------------------------------

    @staticmethod
    def _date_range(filters: QueryFilters | None) -> tuple[str, str]:
        date_start = filters.date_start if filters else None
        date_end = filters.date_end if filters else None
        if not date_start:
            date_start = (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%d")
        if not date_end:
            date_end = datetime.utcnow().strftime("%Y-%m-%d")
        return date_start, date_end
