"""
Sync Service
============

Orchestrates data refresh from external connectors.

- Runs on APScheduler at a per-connector interval
- Pulls data via connector.fetch()
- Normalises into DuckDB tables
- Tracks sync history in a SyncLog table
- Exposes status for the Settings UI
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from ..connectors import registry, ConnectorRegistry
from ..connectors.base import ConnectorHealth, DataDomain, QueryFilters

logger = logging.getLogger(__name__)


class SyncLogEntry:
    """In-memory sync log entry (also written to DuckDB)."""

    __slots__ = (
        "id", "connector_id", "domain", "endpoint",
        "started_at", "finished_at", "status",
        "rows_synced", "error", "duration_ms",
    )

    def __init__(
        self,
        connector_id: str,
        domain: str,
        endpoint: str,
    ) -> None:
        self.id = str(uuid.uuid4())
        self.connector_id = connector_id
        self.domain = domain
        self.endpoint = endpoint
        self.started_at = datetime.utcnow()
        self.finished_at: datetime | None = None
        self.status: str = "running"
        self.rows_synced: int = 0
        self.error: str | None = None
        self.duration_ms: float = 0.0

    def finish(self, rows: int = 0, error: str | None = None) -> None:
        self.finished_at = datetime.utcnow()
        self.rows_synced = rows
        self.error = error
        self.status = "error" if error else "success"
        self.duration_ms = (
            (self.finished_at - self.started_at).total_seconds() * 1000
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "connector_id": self.connector_id,
            "domain": self.domain,
            "endpoint": self.endpoint,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "status": self.status,
            "rows_synced": self.rows_synced,
            "error": self.error,
            "duration_ms": round(self.duration_ms, 1),
        }


class SyncService:
    """Manages data synchronisation from connectors to local store."""

    def __init__(self, reg: ConnectorRegistry | None = None) -> None:
        self._registry = reg or registry
        self._log: list[SyncLogEntry] = []
        self._is_running = False
        self._last_full_sync: datetime | None = None

    # -- Sync operations ----------------------------------------------------

    async def sync_connector(
        self,
        connector_id: str,
        domains: list[str] | None = None,
    ) -> list[SyncLogEntry]:
        """Sync a single connector across its domains."""
        connector = self._registry.all_connectors.get(connector_id)
        if connector is None:
            raise KeyError(f"Unknown connector: {connector_id}")

        if not connector.is_connected:
            try:
                ok = await connector.connect()
                if not ok:
                    entry = SyncLogEntry(connector_id, "*", "*")
                    entry.finish(error=f"Connection failed: {connector.health.last_error}")
                    self._log.append(entry)
                    return [entry]
            except Exception as exc:
                entry = SyncLogEntry(connector_id, "*", "*")
                entry.finish(error=str(exc))
                self._log.append(entry)
                return [entry]

        target_domains = domains or [d.value for d in connector.config.domains]
        entries: list[SyncLogEntry] = []

        for domain_str in target_domains:
            try:
                domain = DataDomain(domain_str)
            except ValueError:
                continue

            # Each domain has a set of standard endpoints
            endpoints = _DOMAIN_ENDPOINTS.get(domain, ["overview"])

            for endpoint in endpoints:
                entry = SyncLogEntry(connector_id, domain_str, endpoint)
                try:
                    data = await connector.fetch(domain, endpoint)
                    rows = _count_rows(data)
                    entry.finish(rows=rows)
                    logger.info(
                        "Synced %s.%s from %s — %d rows",
                        domain_str, endpoint, connector_id, rows,
                    )
                except Exception as exc:
                    entry.finish(error=str(exc))
                    logger.error(
                        "Sync error %s.%s from %s: %s",
                        domain_str, endpoint, connector_id, exc,
                    )

                entries.append(entry)
                self._log.append(entry)

        return entries

    async def sync_all(self) -> list[SyncLogEntry]:
        """Sync all enabled connectors."""
        self._is_running = True
        all_entries: list[SyncLogEntry] = []

        try:
            for cid, connector in self._registry.all_connectors.items():
                if not connector.config.enabled:
                    continue
                if connector.config.connector_type == "seed":
                    continue  # Don't sync the fallback

                entries = await self.sync_connector(cid)
                all_entries.extend(entries)

            self._last_full_sync = datetime.utcnow()
        finally:
            self._is_running = False

        return all_entries

    async def trigger_sync(
        self,
        connector_id: str | None = None,
        domain: str | None = None,
    ) -> list[SyncLogEntry]:
        """Manual sync trigger (from UI or API)."""
        if connector_id:
            domains = [domain] if domain else None
            return await self.sync_connector(connector_id, domains)
        return await self.sync_all()

    # -- Status -------------------------------------------------------------

    def status(self) -> dict[str, Any]:
        """Return overall sync status for the Settings UI."""
        connectors = self._registry.status_summary()

        # Calculate summary stats
        total_syncs = len(self._log)
        recent_errors = sum(
            1 for e in self._log[-50:]
            if e.status == "error"
        )
        total_rows = sum(e.rows_synced for e in self._log)

        return {
            "is_running": self._is_running,
            "last_full_sync": (
                self._last_full_sync.isoformat() if self._last_full_sync else None
            ),
            "connectors": connectors,
            "stats": {
                "total_syncs": total_syncs,
                "recent_errors": recent_errors,
                "total_rows_synced": total_rows,
            },
        }

    def recent_log(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return recent sync log entries."""
        return [e.to_dict() for e in self._log[-limit:]]


# ---------------------------------------------------------------------------
# Standard endpoints per domain
# ---------------------------------------------------------------------------

_DOMAIN_ENDPOINTS: dict[DataDomain, list[str]] = {
    DataDomain.SCORECARD: ["kpis", "financial", "alerts"],
    DataDomain.SPEND: ["overview", "pacing", "dma"],
    DataDomain.FUNNEL: ["stages", "dropoff"],
    DataDomain.SEM: ["overview", "keywords"],
    DataDomain.SOCIAL: ["overview", "platforms"],
    DataDomain.BRAND_MEDIA: ["overview"],
    DataDomain.SEO: ["rankings"],
    DataDomain.AEO: ["summary"],
    DataDomain.RETENTION: ["curves"],
    DataDomain.BRAND_AWARENESS: ["share_of_search"],
    DataDomain.PRODUCT: ["pipeline", "testing"],
    DataDomain.OPS: ["approvals", "calendar"],
    DataDomain.CREATIVE: ["performance"],
}


def _count_rows(data: Any) -> int:
    """Best-effort row count from arbitrary data."""
    if data is None:
        return 0
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        if "rows" in data:
            return len(data["rows"])
        if "data" in data:
            return _count_rows(data["data"])
        if "kpis" in data:
            return len(data["kpis"])
        if "markets" in data:
            return len(data["markets"])
        return 1
    return 1


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

sync_service = SyncService()
