"""CompetitiveIntelItem — Operations Command Center competitive intelligence model.

Tracks competitive signals, rate changes, product launches, and marketing
moves surfaced for the ops team's awareness.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import Field

from src.models.base import ApexBase


class IntelCategory(str, Enum):
    RATE_CHANGE = "rate_change"
    PRODUCT_LAUNCH = "product_launch"
    MARKETING_CAMPAIGN = "marketing_campaign"
    BRANCH_EXPANSION = "branch_expansion"
    PARTNERSHIP = "partnership"
    REGULATORY = "regulatory"
    OTHER = "other"


class IntelImpact(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CompetitiveIntelItem(ApexBase):
    """A competitive intelligence signal for the Operations Command Center."""

    competitor_name: str = Field(min_length=1, description="Name of the competitor")
    category: IntelCategory
    impact: IntelImpact = IntelImpact.MEDIUM

    headline: str = Field(min_length=1, max_length=500, description="Short summary of the signal")
    detail: Optional[str] = Field(default=None, description="Extended context or analysis")
    source_url: Optional[str] = Field(default=None, description="Primary source URL")
    observed_date: date = Field(description="Date the signal was observed")

    product_affected: Optional[str] = Field(
        default=None, description="Product line most affected (e.g. 'checking', 'mortgage')"
    )
    rate_delta_bps: Optional[int] = Field(
        default=None,
        description="Basis-point rate change if category is rate_change (positive = increase)",
    )
    response_recommended: Optional[str] = Field(
        default=None, description="Suggested internal response action"
    )
    is_actioned: bool = Field(
        default=False, description="Whether the ops team has taken action on this signal"
    )
