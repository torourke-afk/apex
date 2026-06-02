"""SocialCreative — one row per paid social creative asset.

Tracks CTR, CVR, spend, and underperformer flag (CTR < platform median).
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field

from src.models.base import ApexBase
from src.models.social_platform_metric import SocialPlatform


class SocialCreative(ApexBase):
    """A single paid social creative and its performance metrics."""

    creative_id: str = Field(min_length=1)
    platform: SocialPlatform
    name: str = Field(min_length=1)
    format: str = Field(description="image | video | carousel")

    ctr: Decimal = Field(ge=0, le=1, decimal_places=6)
    cvr: Decimal = Field(ge=0, le=1, decimal_places=6)
    spend: Decimal = Field(ge=0, decimal_places=2)
    impressions: int = Field(ge=0)
    is_underperformer: bool = Field(description="True when CTR < platform median")
