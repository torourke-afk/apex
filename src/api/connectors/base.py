"""
Base connector interface and shared types.

Every external data source implements ``BaseConnector``.  The connector
contract is intentionally thin — connectors fetch raw data and the BFF
routers handle shaping it for the frontend.
"""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


# ---------------------------------------------------------------------------
# Data domains — the logical categories of data the BFF serves
# ---------------------------------------------------------------------------

class DataDomain(str, enum.Enum):
    """Logical data domains that connectors can serve."""

    SCORECARD = "scorecard"
    SPEND = "spend"
    FUNNEL = "funnel"
    SEM = "sem"
    SOCIAL = "social"
    BRAND_MEDIA = "brand_media"
    SEO = "seo"
    AEO = "aeo"
    RETENTION = "retention"
    BRAND_AWARENESS = "brand_awareness"
    PRODUCT = "product"
    OPS = "ops"
    CREATIVE = "creative"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class ConnectorConfig:
    """Configuration for a single connector instance."""

    connector_type: str                          # e.g. "google_analytics_4"
    display_name: str                            # human-readable label
    domains: list[DataDomain]                    # which domains this connector feeds
    credentials: dict[str, str] = field(
        default_factory=dict,
    )  # api_key, client_id, etc.
    settings: dict[str, Any] = field(
        default_factory=dict,
    )  # connector-specific settings
    enabled: bool = True
    refresh_interval_minutes: int = 15           # how often to sync


# ---------------------------------------------------------------------------
# Health status
# ---------------------------------------------------------------------------

HealthStatus = Literal["connected", "degraded", "disconnected", "error"]


@dataclass
class ConnectorHealth:
    """Current health of a connector."""

    status: HealthStatus
    last_sync: datetime | None = None
    last_error: str | None = None
    rows_synced: int = 0
    latency_ms: float | None = None
    details: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Filter protocol
# ---------------------------------------------------------------------------

@dataclass
class QueryFilters:
    """Standardized filter bag passed to every connector fetch call."""

    date_start: str | None = None   # ISO date
    date_end: str | None = None     # ISO date
    products: list[str] | None = None
    dmas: list[str] | None = None
    channels: list[str] | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_query_params(
        cls,
        date_start: str | None = None,
        date_end: str | None = None,
        product: str | None = None,
        dma: str | None = None,
        channel: str | None = None,
        **extra: Any,
    ) -> "QueryFilters":
        """Build from the standard BFF query parameters."""
        return cls(
            date_start=date_start,
            date_end=date_end,
            products=[p.strip() for p in product.split(",")] if product else None,
            dmas=[d.strip() for d in dma.split(",")] if dma else None,
            channels=[c.strip() for c in channel.split(",")] if channel else None,
            extra=extra,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to the dict format the existing spend_queries etc. expect."""
        d: dict[str, Any] = {}
        if self.date_start:
            d["date_start"] = self.date_start
        if self.date_end:
            d["date_end"] = self.date_end
        if self.dmas:
            d["dma"] = self.dmas
        if self.products:
            d["product"] = self.products
        if self.channels:
            d["channel"] = self.channels
        d.update(self.extra)
        return d or None  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class BaseConnector(ABC):
    """Interface every data-source connector must implement."""

    def __init__(self, config: ConnectorConfig) -> None:
        self.config = config
        self._health = ConnectorHealth(status="disconnected")

    # -- Lifecycle ----------------------------------------------------------

    @abstractmethod
    async def connect(self) -> bool:
        """Initialise connection / validate credentials.  Return True on success."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Tear down resources."""

    @abstractmethod
    async def health_check(self) -> ConnectorHealth:
        """Return current health status."""

    # -- Data fetching ------------------------------------------------------

    @abstractmethod
    async def fetch(
        self,
        domain: DataDomain,
        endpoint: str,
        filters: QueryFilters | None = None,
    ) -> Any:
        """
        Fetch data for a given domain + logical endpoint.

        Parameters
        ----------
        domain : DataDomain
            The data domain being requested (spend, funnel, etc.).
        endpoint : str
            A sub-key within the domain (e.g. "overview", "pacing", "dma").
        filters : QueryFilters | None
            Standardized filters — date range, product, DMA, channel.

        Returns
        -------
        Any
            The raw data payload.  Shape depends on domain + endpoint.
            May be dict, list[dict], DataFrame, etc.
        """

    # -- Metadata -----------------------------------------------------------

    @property
    def id(self) -> str:
        """Unique identifier for this connector instance."""
        return f"{self.config.connector_type}:{self.config.display_name}"

    @property
    def health(self) -> ConnectorHealth:
        return self._health

    @property
    def is_connected(self) -> bool:
        return self._health.status in ("connected", "degraded")

    def supports_domain(self, domain: DataDomain) -> bool:
        return domain in self.config.domains
