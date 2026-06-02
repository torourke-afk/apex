"""LifeEventCampaign — targeted campaign for a major life-stage trigger.

Tracks CVR uplift vs. mass-market baseline and segment parameters used
for audience construction.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, Dict

from pydantic import Field

from src.models.base import ApexBase


class LifeEventType(str, Enum):
    HOME_PURCHASE = "HomePurchase"
    MARRIAGE = "Marriage"
    NEW_CHILD = "NewChild"
    COLLEGE = "College"
    INHERITANCE = "Inheritance"
    JOB_CHANGE = "JobChange"
    DIVORCE = "Divorce"
    RETIREMENT = "Retirement"


class LifeEventCampaign(ApexBase):
    """Performance of a life-event-triggered campaign for one period."""

    event_type: LifeEventType
    period: date
    status: str = Field(description="active | paused")

    cvr: Decimal = Field(ge=0, le=1, decimal_places=6, description="Life-event campaign CVR")
    mass_market_cvr: Decimal = Field(ge=0, le=1, decimal_places=6, description="Baseline mass-market CVR")
    cvr_multiplier: Decimal = Field(ge=0, decimal_places=2, description="CVR / mass_market_cvr; target 2–3×")

    segment_size: int = Field(ge=0)
    segment_parameters: Dict[str, Any] = Field(default_factory=dict, description="Audience construction parameters (JSON)")
