"""
Apex Data Sync Service
======================

Manages scheduled data refresh from external connectors into the
local DuckDB data layer.  Exposes BFF endpoints for status and
manual trigger.
"""

from .service import SyncService, sync_service

__all__ = ["SyncService", "sync_service"]
