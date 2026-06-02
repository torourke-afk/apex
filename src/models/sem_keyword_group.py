"""SEMKeywordGroup — SEM keyword group definition and configuration.

Represents a logical grouping of semantically related keywords for paid search.
Each group has a match type, product category, intent classification, and
bid/quality settings.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import Field

from src.models.base import ApexBase


class SEMMatchType(str, Enum):
    BROAD = "broad"
    PHRASE = "phrase"
    EXACT = "exact"


class SEMIntentType(str, Enum):
    BRANDED = "branded"
    NON_BRANDED = "non_branded"
    PMAX = "pmax"


class SEMKeywordGroup(ApexBase):
    """Configuration record for a SEM keyword group."""

    name: str = Field(min_length=1, description="Descriptive name for the keyword group")
    product_category: str = Field(
        min_length=1,
        description="Product category targeted (e.g. checking, mortgage, credit_card)",
    )
    intent_type: SEMIntentType = Field(
        description="Keyword intent classification: branded, non_branded, or pmax"
    )
    match_type: SEMMatchType = Field(
        description="Google Ads match type: broad, phrase, or exact"
    )
    max_cpc: Decimal = Field(
        gt=Decimal("0"),
        decimal_places=2,
        description="Maximum cost-per-click bid in USD",
    )
    quality_score: int = Field(
        ge=3,
        le=10,
        description="Google Ads quality score (3–10)",
    )
    estimated_monthly_volume: int = Field(
        ge=0,
        description="Estimated monthly search volume for the group",
    )
    market_segment: Literal["established", "growth", "new"] = Field(
        description="Market maturity segment: established, growth, or new",
    )
    is_active: bool = Field(
        default=True,
        description="Whether the group is currently active",
    )
    dma: str | None = Field(
        default=None,
        description="DMA geo-target, or None for national targeting",
    )
