"""ProductInitiative — tracks strategic product initiatives for the Product & Experience module."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import Field

from src.models.base import ApexBase


class InitiativeStatus(str, Enum):
    discovery = "discovery"
    in_progress = "in_progress"
    launched = "launched"
    paused = "paused"
    cancelled = "cancelled"


class InitiativePriority(str, Enum):
    p0 = "p0"
    p1 = "p1"
    p2 = "p2"
    p3 = "p3"


class ProductInitiative(ApexBase):
    """A strategic product initiative tied to a product area and success metric."""

    title: str
    description: str
    status: InitiativeStatus
    priority: InitiativePriority
    product_area: str
    owner: str
    target_launch_date: date
    actual_launch_date: Optional[date] = None
    hypothesis: str
    success_metric: str
    baseline_value: Decimal = Field(decimal_places=4)
    target_value: Decimal = Field(decimal_places=4)
    actual_value: Optional[Decimal] = Field(default=None, decimal_places=4)
