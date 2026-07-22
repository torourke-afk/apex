"""
Google Analytics 4 Connector
=============================

Pulls session, conversion, and traffic data from GA4 Data API.
Maps to: scorecard, funnel, spend domains.

Required credentials (env vars):
    GA4_PROPERTY_ID       — GA4 property numeric ID
    GA4_CREDENTIALS_JSON  — path to service account JSON key file
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

_DEFAULT_PROPERTY_ID = os.environ.get("GA4_PROPERTY_ID", "")
_DEFAULT_CREDENTIALS = os.environ.get("GA4_CREDENTIALS_JSON", "")


def default_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_type="google_analytics_4",
        display_name="Google Analytics 4",
        domains=[DataDomain.SCORECARD, DataDomain.FUNNEL, DataDomain.SPEND],
        credentials={
            "property_id": _DEFAULT_PROPERTY_ID,
            "credentials_json": _DEFAULT_CREDENTIALS,
        },
        settings={
            "date_range_days": 90,
            "dimensions": ["date", "sessionDefaultChannelGroup", "city"],
        },
        enabled=bool(_DEFAULT_PROPERTY_ID and _DEFAULT_CREDENTIALS),
        refresh_interval_minutes=30,
    )


class GoogleAnalytics4Connector(BaseConnector):
    """Connector for GA4 Data API (google-analytics-data)."""

    def __init__(self, config: ConnectorConfig | None = None) -> None:
        super().__init__(config or default_config())
        self._client: Any = None

    # -- Lifecycle ----------------------------------------------------------

    async def connect(self) -> bool:
        prop_id = self.config.credentials.get("property_id")
        creds_path = self.config.credentials.get("credentials_json")

        if not prop_id or not creds_path:
            self._health = ConnectorHealth(
                status="disconnected",
                last_error="Missing GA4_PROPERTY_ID or GA4_CREDENTIALS_JSON",
            )
            return False

        try:
            from google.analytics.data_v1beta import BetaAnalyticsDataClient
            from google.oauth2 import service_account

            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=["https://www.googleapis.com/auth/analytics.readonly"],
            )
            self._client = BetaAnalyticsDataClient(credentials=credentials)

            # Validate by running a minimal request
            from google.analytics.data_v1beta.types import (
                DateRange,
                Dimension,
                Metric,
                RunReportRequest,
            )

            req = RunReportRequest(
                property=f"properties/{prop_id}",
                date_ranges=[DateRange(start_date="yesterday", end_date="today")],
                dimensions=[Dimension(name="date")],
                metrics=[Metric(name="sessions")],
                limit=1,
            )
            self._client.run_report(req)

            self._health = ConnectorHealth(
                status="connected",
                last_sync=datetime.utcnow(),
                details={"property_id": prop_id},
            )
            return True

        except ImportError:
            self._health = ConnectorHealth(
                status="error",
                last_error=(
                    "google-analytics-data package not installed. "
                    "Run: pip install google-analytics-data"
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

        prop_id = self.config.credentials["property_id"]

        try:
            from google.analytics.data_v1beta.types import (
                DateRange,
                Dimension,
                FilterExpression,
                Filter as GA4Filter,
                Metric,
                RunReportRequest,
            )

            # Default date range
            date_start = filters.date_start if filters else None
            date_end = filters.date_end if filters else None
            if not date_start:
                date_start = (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%d")
            if not date_end:
                date_end = datetime.utcnow().strftime("%Y-%m-%d")

            dispatch = {
                ("scorecard", "kpis"): self._fetch_scorecard_kpis,
                ("funnel", "stages"): self._fetch_funnel_stages,
                ("spend", "overview"): self._fetch_spend_overview,
            }

            handler = dispatch.get((domain.value, endpoint))
            if handler is None:
                logger.warning("GA4: no handler for %s.%s", domain.value, endpoint)
                return None

            result = await handler(prop_id, date_start, date_end, filters)
            self._health.last_sync = datetime.utcnow()
            return result

        except Exception as exc:
            logger.error("GA4 fetch error (%s.%s): %s", domain.value, endpoint, exc)
            self._health.last_error = str(exc)
            self._health.status = "degraded"
            return None

    # -- GA4 fetch implementations ------------------------------------------

    async def _fetch_scorecard_kpis(
        self,
        prop_id: str,
        date_start: str,
        date_end: str,
        filters: QueryFilters | None,
    ) -> list[dict]:
        """Fetch high-level KPIs from GA4."""
        from google.analytics.data_v1beta.types import (
            DateRange,
            Metric,
            RunReportRequest,
        )

        req = RunReportRequest(
            property=f"properties/{prop_id}",
            date_ranges=[DateRange(start_date=date_start, end_date=date_end)],
            metrics=[
                Metric(name="sessions"),
                Metric(name="totalUsers"),
                Metric(name="conversions"),
                Metric(name="totalRevenue"),
            ],
        )
        response = self._client.run_report(req)
        row = response.rows[0] if response.rows else None
        if not row:
            return []

        return [
            {
                "label": "Sessions",
                "value": int(row.metric_values[0].value),
                "delta": 0,
                "format": "number",
            },
            {
                "label": "Users",
                "value": int(row.metric_values[1].value),
                "delta": 0,
                "format": "number",
            },
            {
                "label": "Conversions",
                "value": int(row.metric_values[2].value),
                "delta": 0,
                "format": "number",
            },
            {
                "label": "Revenue",
                "value": float(row.metric_values[3].value),
                "delta": 0,
                "format": "currency",
            },
        ]

    async def _fetch_funnel_stages(
        self,
        prop_id: str,
        date_start: str,
        date_end: str,
        filters: QueryFilters | None,
    ) -> list[dict]:
        """Fetch funnel stages from GA4 events."""
        from google.analytics.data_v1beta.types import (
            DateRange,
            Dimension,
            Metric,
            RunReportRequest,
        )

        # GA4 funnel: map event names to funnel stages
        req = RunReportRequest(
            property=f"properties/{prop_id}",
            date_ranges=[DateRange(start_date=date_start, end_date=date_end)],
            dimensions=[Dimension(name="eventName")],
            metrics=[Metric(name="eventCount"), Metric(name="eventValue")],
        )
        response = self._client.run_report(req)

        stages = []
        for row in response.rows:
            stages.append({
                "event_name": row.dimension_values[0].value,
                "count": int(row.metric_values[0].value),
                "value": float(row.metric_values[1].value),
            })

        return stages

    async def _fetch_spend_overview(
        self,
        prop_id: str,
        date_start: str,
        date_end: str,
        filters: QueryFilters | None,
    ) -> list[dict]:
        """Fetch session-based channel performance from GA4."""
        from google.analytics.data_v1beta.types import (
            DateRange,
            Dimension,
            Metric,
            RunReportRequest,
        )

        req = RunReportRequest(
            property=f"properties/{prop_id}",
            date_ranges=[DateRange(start_date=date_start, end_date=date_end)],
            dimensions=[Dimension(name="sessionDefaultChannelGroup")],
            metrics=[
                Metric(name="sessions"),
                Metric(name="conversions"),
                Metric(name="totalRevenue"),
            ],
        )
        response = self._client.run_report(req)

        channels = []
        for row in response.rows:
            channels.append({
                "channel": row.dimension_values[0].value,
                "sessions": int(row.metric_values[0].value),
                "conversions": int(row.metric_values[1].value),
                "revenue": float(row.metric_values[2].value),
            })

        return channels
