"""BehavioralTrigger — automated marketing triggers fired on customer behavior signals."""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field

from src.models.base import ApexBase


class BehavioralTrigger(ApexBase):
    """Represents a single automated trigger definition and its performance metrics."""

    trigger_name: str
    condition: str = Field(description="Human-readable condition expression")
    action: str = Field(description="Action taken when trigger fires")
    volume_per_week: int = Field(ge=0)
    conversion_rate: Decimal = Field(ge=0, le=1, decimal_places=4)
    period: str = Field(
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="ISO month YYYY-MM",
    )
