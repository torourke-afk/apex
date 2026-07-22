"""
Sync & Connector Management API Router
=======================================

Endpoints:
    GET  /api/sync/status       — overall sync status + connector health
    GET  /api/sync/log          — recent sync log entries
    POST /api/sync/trigger      — trigger manual sync
    GET  /api/connectors        — list all connectors with status
    POST /api/connectors/health — run health checks on all connectors
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query

from .service import sync_service
from ..connectors import registry
from ..connectors.base import DataDomain

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sync"])


# ---------------------------------------------------------------------------
# Sync endpoints
# ---------------------------------------------------------------------------

@router.get("/api/sync/status")
def get_sync_status() -> dict[str, Any]:
    """Return overall sync status — connector health, stats, last sync time."""
    return sync_service.status()


@router.get("/api/sync/log")
def get_sync_log(
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    """Return recent sync log entries."""
    return {"entries": sync_service.recent_log(limit)}


@router.post("/api/sync/trigger")
async def trigger_sync(
    connector_id: str | None = Query(default=None),
    domain: str | None = Query(default=None),
) -> dict[str, Any]:
    """Manually trigger a sync.

    - No params: sync all enabled connectors.
    - ``connector_id``: sync a specific connector.
    - ``connector_id`` + ``domain``: sync a specific domain on a connector.
    """
    try:
        entries = await sync_service.trigger_sync(connector_id, domain)
        return {
            "success": True,
            "entries": [e.to_dict() for e in entries],
        }
    except KeyError as exc:
        return {"success": False, "error": str(exc)}
    except Exception as exc:
        logger.error("Sync trigger failed: %s", exc)
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Connector management endpoints
# ---------------------------------------------------------------------------

@router.get("/api/connectors")
def list_connectors() -> dict[str, Any]:
    """List all registered connectors with their status."""
    return {
        "connectors": registry.status_summary(),
        "domain_assignments": registry.domain_assignments,
        "available_domains": [d.value for d in DataDomain],
    }


@router.post("/api/connectors/health")
async def run_health_checks() -> dict[str, Any]:
    """Run health checks on all connectors."""
    results = await registry.health_check_all()
    return {
        "results": {
            cid: {
                "status": h.status,
                "last_sync": h.last_sync.isoformat() if h.last_sync else None,
                "last_error": h.last_error,
                "latency_ms": h.latency_ms,
            }
            for cid, h in results.items()
        }
    }


@router.get("/api/connectors/{connector_id}")
def get_connector_detail(connector_id: str) -> dict[str, Any]:
    """Get detailed status for a single connector."""
    connector = registry.all_connectors.get(connector_id)
    if connector is None:
        return {"error": f"Unknown connector: {connector_id}"}

    h = connector.health
    domains_served = [
        d for d, cid in registry.domain_assignments.items()
        if cid == connector_id
    ]

    return {
        "id": connector_id,
        "type": connector.config.connector_type,
        "display_name": connector.config.display_name,
        "enabled": connector.config.enabled,
        "is_connected": connector.is_connected,
        "domains": domains_served,
        "health": {
            "status": h.status,
            "last_sync": h.last_sync.isoformat() if h.last_sync else None,
            "last_error": h.last_error,
            "rows_synced": h.rows_synced,
            "latency_ms": h.latency_ms,
            "details": h.details,
        },
        "settings": {
            k: v for k, v in connector.config.settings.items()
            if k not in ("api_key", "access_token", "client_secret")
        },
        "refresh_interval_minutes": connector.config.refresh_interval_minutes,
    }
