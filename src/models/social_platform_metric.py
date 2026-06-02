"""SocialPlatformMetric — one row per platform per period.

Tracks paid social performance by platform: spend, impressions, clicks,
leads, CPL, conversion rates, and AI vs. manual CPA comparison.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import Field

from src.models.base import ApexBase


class SocialPlatform(str, Enum):
    META = "Meta"
    TIKTOK = "TikTok"
    LINKEDIN = "LinkedIn"
    OTHER = "Other"


class SocialPlatformMetric(ApexBase):
    """Paid social performance for one platform in one reporting period."""

    platform: SocialPlatform
    period: date

    spend: Decimal = Field(ge=0, decimal_places=2)
    impressions: int = Field(ge=0)
    clicks: int = Field(ge=0)
    leads: int = Field(ge=0)
    cpl: Decimal = Field(ge=0, decimal_places=2, description="Cost per lead")
    cvr_native: Decimal = Field(ge=0, le=1, decimal_places=6, description="Native lead-form CVR")
    cvr_landing: Decimal = Field(ge=0, le=1, decimal_places=6, description="Landing page CVR")
    cpa_ai: Decimal = Field(ge=0, decimal_places=2, description="AI-optimized CPA")
    cpa_manual: Decimal = Field(ge=0, decimal_places=2, description="Manual CPA")
    first_party_audiences: int = Field(ge=0, description="Matched 1P audience size")
