"""RoadmapItem — a quarterly roadmap deliverable linked to a ProductInitiative."""

from __future__ import annotations

from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import Field, field_validator

from src.models.base import ApexBase

_VALID_QUARTERS = {f"{y}-Q{q}" for y in range(2024, 2029) for q in range(1, 5)}


class RoadmapStatus(str, Enum):
    planned = "planned"
    in_flight = "in_flight"
    complete = "complete"
    deferred = "deferred"


class RoadmapPriority(str, Enum):
    must_have = "must_have"
    should_have = "should_have"
    nice_to_have = "nice_to_have"


class RoadmapItem(ApexBase):
    """A single quarterly roadmap item tied to a product initiative."""

    initiative_id: UUID
    quarter: str  # e.g. "2026-Q2"
    title: str
    status: RoadmapStatus
    team: str
    effort_points: int = Field(ge=1, le=21)
    priority: RoadmapPriority
    milestone: Optional[str] = None

    @field_validator("quarter")
    @classmethod
    def validate_quarter(cls, v: str) -> str:
        if v not in _VALID_QUARTERS:
            raise ValueError(f"quarter must be YYYY-QN (2024–2028), got {v!r}")
        return v
