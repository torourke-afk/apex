"""ABTest — tracks A/B and multivariate experiments for the Product & Experience module."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import Field, model_validator

from src.models.base import ApexBase


class ABTestStatus(str, Enum):
    draft = "draft"
    running = "running"
    complete = "complete"
    stopped = "stopped"


class ABTest(ApexBase):
    """An A/B or multivariate test with outcome tracking."""

    test_name: str
    hypothesis: str
    product_area: str
    status: ABTestStatus
    variant_count: int = Field(ge=2, le=5)
    start_date: date
    end_date: Optional[date] = None
    sample_size: int = Field(ge=0)
    traffic_allocation_pct: Decimal = Field(ge=0, le=1, decimal_places=4)
    primary_metric: str
    control_rate: Decimal = Field(ge=0, le=1, decimal_places=6)
    treatment_rate: Optional[Decimal] = Field(default=None, decimal_places=6)
    lift_pct: Optional[Decimal] = Field(default=None, decimal_places=4)
    p_value: Optional[Decimal] = Field(default=None, ge=0, le=1, decimal_places=6)
    is_significant: Optional[bool] = None
    winner: Optional[str] = None

    @model_validator(mode="after")
    def end_after_start(self) -> "ABTest":
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self
