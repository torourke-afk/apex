"""CalendarEvent — Operations Command Center scheduled event model.

Tracks marketing campaign launches, review cycles, compliance deadlines,
and executive briefings on the ops calendar.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import Field, model_validator

from src.models.base import ApexBase


class EventType(str, Enum):
    CAMPAIGN_LAUNCH = "campaign_launch"
    REVIEW_CYCLE = "review_cycle"
    COMPLIANCE_DEADLINE = "compliance_deadline"
    EXEC_BRIEFING = "exec_briefing"
    BUDGET_REVIEW = "budget_review"
    TEAM_SYNC = "team_sync"
    OTHER = "other"


class EventStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CalendarEvent(ApexBase):
    """An ops calendar event tracked in the Operations Command Center."""

    title: str = Field(min_length=1, max_length=255, description="Event title")
    event_type: EventType
    status: EventStatus = EventStatus.SCHEDULED

    start_dt: datetime = Field(description="Event start (UTC)")
    end_dt: datetime = Field(description="Event end (UTC)")

    owner: str = Field(min_length=1, description="Primary owner / DRI")
    attendees: Optional[str] = Field(
        default=None,
        description="Comma-separated list of attendee names or emails",
    )
    description: Optional[str] = Field(default=None, description="Event notes")
    related_campaign_id: Optional[str] = Field(
        default=None, description="Linked campaign UUID if applicable"
    )

    @model_validator(mode="after")
    def _end_after_start(self) -> "CalendarEvent":
        if self.end_dt <= self.start_dt:
            raise ValueError("end_dt must be after start_dt")
        return self
