"""
Generic REST Connector
======================

Connects to any JSON REST API endpoint.  Useful for:
- Internal data warehouses / BI tools
- Custom ETL webhooks
- Third-party data providers (Datorama, Funnel.io, etc.)

Configuration:
    base_url   — API root (e.g. "https://api.example.com/v1")
    auth_type  — "bearer", "api_key", "basic", or "none"
    auth_value — token / key / base64(user:pass)
    endpoints  — mapping of domain.endpoint → relative URL + method
"""

from __future__ import annotations

import logging
import os
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


class GenericRESTConnector(BaseConnector):
    """Connector for arbitrary JSON REST APIs."""

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)
        self._session: Any = None

    # -- Lifecycle ----------------------------------------------------------

    async def connect(self) -> bool:
        base_url = self.config.settings.get("base_url")
        if not base_url:
            self._health = ConnectorHealth(
                status="disconnected",
                last_error="No base_url configured",
            )
            return False

        try:
            import httpx

            # Build auth headers
            headers: dict[str, str] = {"Accept": "application/json"}
            auth_type = self.config.credentials.get("auth_type", "none")
            auth_value = self.config.credentials.get("auth_value", "")

            if auth_type == "bearer" and auth_value:
                headers["Authorization"] = f"Bearer {auth_value}"
            elif auth_type == "api_key" and auth_value:
                key_name = self.config.credentials.get("api_key_header", "X-API-Key")
                headers[key_name] = auth_value
            elif auth_type == "basic" and auth_value:
                headers["Authorization"] = f"Basic {auth_value}"

            self._session = httpx.AsyncClient(
                base_url=base_url,
                headers=headers,
                timeout=30.0,
            )

            # Health check — try the health endpoint if configured, else HEAD /
            health_path = self.config.settings.get("health_path", "/")
            resp = await self._session.head(health_path)

            if resp.status_code >= 400:
                self._health = ConnectorHealth(
                    status="error",
                    last_error=f"Health check returned {resp.status_code}",
                )
                return False

            self._health = ConnectorHealth(
                status="connected",
                last_sync=datetime.utcnow(),
                details={"base_url": base_url},
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

        # Look up the endpoint mapping
        endpoints_map: dict[str, dict] = self.config.settings.get("endpoints", {})
        key = f"{domain.value}.{endpoint}"
        ep_config = endpoints_map.get(key)

        if ep_config is None:
            logger.warning("GenericREST: no endpoint mapped for %s", key)
            return None

        path = ep_config.get("path", "")
        method = ep_config.get("method", "GET").upper()

        # Build query params from filters
        params: dict[str, str] = {}
        if filters:
            if filters.date_start:
                params["date_start"] = filters.date_start
            if filters.date_end:
                params["date_end"] = filters.date_end
            if filters.dmas:
                params["dma"] = ",".join(filters.dmas)
            if filters.products:
                params["product"] = ",".join(filters.products)
            if filters.channels:
                params["channel"] = ",".join(filters.channels)

        # Add any static params from config
        static_params = ep_config.get("params", {})
        params.update(static_params)

        try:
            if method == "GET":
                resp = await self._session.get(path, params=params)
            elif method == "POST":
                resp = await self._session.post(path, json=params)
            else:
                resp = await self._session.request(method, path, params=params)

            resp.raise_for_status()
            data = resp.json()

            self._health.last_sync = datetime.utcnow()

            # Apply optional JSONPath extraction
            extract_path = ep_config.get("extract")
            if extract_path:
                for key_part in extract_path.split("."):
                    if isinstance(data, dict):
                        data = data.get(key_part)
                    elif isinstance(data, list) and key_part.isdigit():
                        data = data[int(key_part)]

            return data

        except Exception as exc:
            logger.error("GenericREST fetch error (%s): %s", key, exc)
            self._health.last_error = str(exc)
            self._health.status = "degraded"
            return None
