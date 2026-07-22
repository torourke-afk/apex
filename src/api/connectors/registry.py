"""
Connector Registry
==================

Singleton that maps data domains to the active connector for each.
BFF routers call ``registry.get(domain)`` to obtain the connector,
then call ``connector.fetch(domain, endpoint, filters)``.

The registry always has a ``SeedConnector`` as fallback — if a real
connector fails or isn't configured, the seed connector serves data.
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


class ConnectorRegistry:
    """Maps data domains → active connector instances."""

    def __init__(self) -> None:
        self._connectors: dict[str, BaseConnector] = {}       # id → connector
        self._domain_map: dict[DataDomain, str] = {}          # domain → connector id
        self._fallback_id: str | None = None                  # seed connector id

    # -- Registration -------------------------------------------------------

    def register(
        self,
        connector: BaseConnector,
        *,
        is_fallback: bool = False,
    ) -> None:
        """Register a connector instance.

        If ``is_fallback=True``, this connector is used for any domain
        that doesn't have a dedicated connector assigned.
        """
        cid = connector.id
        self._connectors[cid] = connector

        if is_fallback:
            self._fallback_id = cid

        # Auto-assign domains that don't already have a non-fallback connector
        for domain in connector.config.domains:
            existing = self._domain_map.get(domain)
            if existing is None or is_fallback:
                # Non-fallback connector takes priority
                if not is_fallback:
                    self._domain_map[domain] = cid
                elif domain not in self._domain_map:
                    self._domain_map[domain] = cid

        logger.info(
            "Registered connector %s (domains=%s, fallback=%s)",
            cid,
            [d.value for d in connector.config.domains],
            is_fallback,
        )

    def unregister(self, connector_id: str) -> None:
        """Remove a connector.  Domains it served revert to fallback."""
        connector = self._connectors.pop(connector_id, None)
        if connector is None:
            return

        # Clean up domain assignments
        for domain, cid in list(self._domain_map.items()):
            if cid == connector_id:
                if self._fallback_id:
                    self._domain_map[domain] = self._fallback_id
                else:
                    del self._domain_map[domain]

        logger.info("Unregistered connector %s", connector_id)

    # -- Assignment ---------------------------------------------------------

    def assign(self, domain: DataDomain, connector_id: str) -> None:
        """Explicitly assign a domain to a specific connector."""
        if connector_id not in self._connectors:
            raise KeyError(f"Unknown connector: {connector_id}")
        self._domain_map[domain] = connector_id

    # -- Lookup -------------------------------------------------------------

    def get(self, domain: DataDomain | str) -> BaseConnector | None:
        """Get the active connector for a domain.  Returns None if nothing is assigned."""
        if isinstance(domain, str):
            domain = DataDomain(domain)

        cid = self._domain_map.get(domain)
        if cid and cid in self._connectors:
            return self._connectors[cid]

        # Fall back
        if self._fallback_id and self._fallback_id in self._connectors:
            return self._connectors[self._fallback_id]

        return None

    def get_or_fallback(self, domain: DataDomain | str) -> BaseConnector:
        """Like ``get`` but raises if nothing available."""
        conn = self.get(domain)
        if conn is None:
            raise RuntimeError(
                f"No connector available for domain '{domain}' "
                "and no fallback registered."
            )
        return conn

    # -- Introspection ------------------------------------------------------

    @property
    def all_connectors(self) -> dict[str, BaseConnector]:
        return dict(self._connectors)

    @property
    def domain_assignments(self) -> dict[str, str]:
        """Return {domain_value: connector_id} map."""
        return {d.value: cid for d, cid in self._domain_map.items()}

    def status_summary(self) -> list[dict[str, Any]]:
        """Return a list of connector status dicts for the Settings UI."""
        results = []
        for cid, conn in self._connectors.items():
            domains_served = [
                d.value for d, assigned_cid in self._domain_map.items()
                if assigned_cid == cid
            ]
            h = conn.health
            results.append({
                "id": cid,
                "type": conn.config.connector_type,
                "display_name": conn.config.display_name,
                "enabled": conn.config.enabled,
                "is_fallback": cid == self._fallback_id,
                "domains": domains_served,
                "status": h.status,
                "last_sync": h.last_sync.isoformat() if h.last_sync else None,
                "last_error": h.last_error,
                "rows_synced": h.rows_synced,
                "latency_ms": h.latency_ms,
                "refresh_interval_minutes": conn.config.refresh_interval_minutes,
            })
        return results

    # -- Lifecycle ----------------------------------------------------------

    async def connect_all(self) -> dict[str, bool]:
        """Connect all registered connectors.  Returns {id: success}."""
        results = {}
        for cid, conn in self._connectors.items():
            if not conn.config.enabled:
                results[cid] = False
                continue
            try:
                ok = await conn.connect()
                results[cid] = ok
                logger.info("Connected %s: %s", cid, ok)
            except Exception as exc:
                results[cid] = False
                logger.warning("Failed to connect %s: %s", cid, exc)
        return results

    async def disconnect_all(self) -> None:
        """Disconnect all connectors."""
        for cid, conn in self._connectors.items():
            try:
                await conn.disconnect()
            except Exception as exc:
                logger.warning("Error disconnecting %s: %s", cid, exc)

    async def health_check_all(self) -> dict[str, ConnectorHealth]:
        """Run health checks on all connectors."""
        results = {}
        for cid, conn in self._connectors.items():
            try:
                results[cid] = await conn.health_check()
            except Exception as exc:
                results[cid] = ConnectorHealth(
                    status="error",
                    last_error=str(exc),
                )
        return results


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

registry = ConnectorRegistry()
