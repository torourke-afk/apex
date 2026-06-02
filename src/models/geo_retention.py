"""GeoRetention — 90-day retention rates by geography for the map visualization."""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field

from src.models.base import ApexBase


class GeoRetention(ApexBase):
    """Retention metric for a single geographic market."""

    geography: str = Field(description="DMA name or market label")
    lat: Decimal = Field(ge=-90, le=90, decimal_places=6)
    lon: Decimal = Field(ge=-180, le=180, decimal_places=6)
    retention_90d: Decimal = Field(ge=0, le=1, decimal_places=4)
    market_tier: str = Field(description="e.g. 'tier_1', 'tier_2', 'tier_3'")
    period: str = Field(
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="ISO month YYYY-MM",
    )
