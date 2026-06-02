"""BrandMarketBEI — Brand Equity Index for one market per week.

Composite BEI is a weighted average of five brand-health component scores.
Active markets are compared against control markets via incrementality_lift.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import Field

from src.models.base import ApexBase


class MarketTier(str, Enum):
    TIER1 = "Tier1"
    TIER2 = "Tier2"
    TIER3 = "Tier3"


class BrandMarketBEI(ApexBase):
    """Weekly brand equity index snapshot for a single market."""

    market_name: str = Field(min_length=1)
    market_tier: MarketTier
    week_ending: date

    # Brand health component scores (0–100)
    awareness_score: Decimal = Field(ge=0, le=100, decimal_places=2)
    branded_search_score: Decimal = Field(ge=0, le=100, decimal_places=2)
    direct_traffic_score: Decimal = Field(ge=0, le=100, decimal_places=2)
    branch_visits_score: Decimal = Field(ge=0, le=100, decimal_places=2)
    social_engagement_score: Decimal = Field(ge=0, le=100, decimal_places=2)

    # Composite
    bei_score: Decimal = Field(ge=0, le=100, decimal_places=2, description="Weighted composite BEI")

    # Media effectiveness
    frequency_compliance: Decimal = Field(ge=0, le=1, decimal_places=4, description="% at effective reach")
    ctv_completion_rate: Decimal = Field(ge=0, le=1, decimal_places=4)
    olv_completion_rate: Decimal = Field(ge=0, le=1, decimal_places=4)
    audio_listen_through_rate: Decimal = Field(ge=0, le=1, decimal_places=4)

    # Test vs. control
    is_active_market: bool = Field(description="True = active market, False = control")
    incrementality_lift: Optional[Decimal] = Field(
        default=None, decimal_places=4, description="Incremental lift vs. control (nullable for control markets)"
    )
