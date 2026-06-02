"""TeamCapacity — Operations Command Center team capacity tracking model.

Tracks headcount, utilization, and bandwidth by team/function for
capacity planning and resource allocation decisions.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import Field, model_validator

from src.models.base import ApexBase


class TeamFunction(str, Enum):
    BRAND = "brand"
    PERFORMANCE_MEDIA = "performance_media"
    SEO_CONTENT = "seo_content"
    ANALYTICS = "analytics"
    CREATIVE = "creative"
    PRODUCT_MARKETING = "product_marketing"
    OPS = "ops"
    OTHER = "other"


class TeamCapacity(ApexBase):
    """Capacity snapshot for a team function in a given period."""

    team_name: str = Field(min_length=1, description="Team or squad name")
    function: TeamFunction
    period: str = Field(
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="ISO month YYYY-MM this snapshot covers",
    )

    headcount_total: int = Field(ge=0, description="Total headcount including contractors")
    headcount_fte: int = Field(ge=0, description="Full-time employees only")
    open_reqs: int = Field(default=0, ge=0, description="Open job requisitions")

    utilization_pct: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("100"),
        decimal_places=2,
        description="Billable / allocated utilization percentage",
    )
    capacity_available_hrs: Optional[int] = Field(
        default=None, ge=0, description="Available hours in the period for new work"
    )
    notes: Optional[str] = Field(default=None, description="Context or caveats for this snapshot")

    @model_validator(mode="after")
    def _fte_lte_total(self) -> "TeamCapacity":
        if self.headcount_fte > self.headcount_total:
            raise ValueError("headcount_fte cannot exceed headcount_total")
        return self
