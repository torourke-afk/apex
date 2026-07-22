"""
Apex Data Connectors
====================

Pluggable connector framework for external data sources.

Architecture
------------
1. ``BaseConnector`` — abstract interface every connector implements.
2. ``ConnectorRegistry`` — singleton that maps data *domains*
   (spend, funnel, sem, social …) to the active connector for each.
3. Concrete connectors:
   - ``SeedConnector`` — wraps the existing DuckDB / in-memory seed layer
     (always available, used as fallback).
   - ``GoogleAnalytics4Connector`` — GA4 Data API.
   - ``SEMrushConnector`` — SEMrush Analytics API.
   - ``GoogleAdsConnector`` — Google Ads API (Keyword Planner + Campaigns).
   - ``MetaAdsConnector`` — Meta Marketing API.
   - ``GenericRESTConnector`` — any JSON REST endpoint.

Usage
-----
    from src.api.connectors import registry

    connector = registry.get("spend")        # returns active connector for spend domain
    data = await connector.fetch("overview")  # fetch data from the source
"""

from .base import BaseConnector, ConnectorConfig, ConnectorHealth, DataDomain
from .registry import ConnectorRegistry, registry
from .seed import SeedConnector

__all__ = [
    "BaseConnector",
    "ConnectorConfig",
    "ConnectorHealth",
    "ConnectorRegistry",
    "DataDomain",
    "SeedConnector",
    "registry",
]
