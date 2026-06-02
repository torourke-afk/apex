"""SEMDailyPerformance — daily paid search performance metrics per keyword group.

One record per (keyword_group_id, date). Captures Google Ads performance
KPIs including impressions, clicks, spend, quality score, auction metrics,
downstream conversions, and VBB margin signal.
"""

from __future__ import annotations

from datetime import date as _date
from decimal import Decimal
from uuid import UUID

from pydantic import Field, model_validator

from src.models.base import ApexBase


class SEMDailyPerformance(ApexBase):
    """Daily SEM performance snapshot for a keyword group."""

    keyword_group_id: UUID = Field(description="FK → SEMKeywordGroup.id")
    date: _date = Field(description="Calendar date of the performance record")

    # Auction metrics
    impressions: int = Field(ge=0, description="Total impressions served")
    clicks: int = Field(ge=0, description="Total clicks received")
    ctr: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("1"),
        decimal_places=6,
        description="Click-through rate (clicks / impressions)",
    )
    cpc: Decimal = Field(
        ge=Decimal("0"),
        decimal_places=4,
        description="Average cost-per-click in USD",
    )
    spend: Decimal = Field(
        ge=Decimal("0"),
        decimal_places=4,
        description="Total spend in USD for the day",
    )
    avg_position: Decimal = Field(
        ge=Decimal("1"),
        le=Decimal("10"),
        decimal_places=2,
        description="Average ad position in SERP (1 = top)",
    )
    impression_share: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("1"),
        decimal_places=4,
        description="Impression share (impressions won / eligible impressions)",
    )
    quality_score: int = Field(
        ge=3,
        le=10,
        description="Google Ads quality score for the group on this day",
    )

    # Conversion metrics
    conversions: int = Field(ge=0, description="Total tracked conversions")
    cvr: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("1"),
        decimal_places=6,
        description="Conversion rate (conversions / clicks)",
    )
    cpl: Decimal = Field(
        ge=Decimal("0"),
        decimal_places=4,
        description="Cost per lead/conversion in USD (0 when no conversions)",
    )

    # VBB business metric
    vbb_margin_signal: float = Field(
        ge=0.0,
        le=1.0,
        description="Value-Based Bidding margin signal [0, 1] — higher = more margin",
    )

    @model_validator(mode="after")
    def clicks_le_impressions(self) -> "SEMDailyPerformance":
        if self.impressions > 0 and self.clicks > self.impressions:
            raise ValueError("clicks cannot exceed impressions")
        return self

    @model_validator(mode="after")
    def conversions_le_clicks(self) -> "SEMDailyPerformance":
        if self.clicks > 0 and self.conversions > self.clicks:
            raise ValueError("conversions cannot exceed clicks")
        return self
