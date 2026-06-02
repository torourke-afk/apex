from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import field_validator

from src.models.base import ApexBase


class DirectiveType(str, Enum):
    budget_reallocation = "budget_reallocation"
    market_tier_change = "market_tier_change"
    channel_mix_adjustment = "channel_mix_adjustment"
    life_event_toggle = "life_event_toggle"
    test_launch = "test_launch"
    recovery_update = "recovery_update"
    offer_strategy = "offer_strategy"


_VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"approved", "cancelled"},
    "approved": {"in_progress", "cancelled"},
    "in_progress": {"completed", "failed"},
    "completed": set(),
    "failed": set(),
    "cancelled": set(),
}


class InvalidTransitionError(ValueError):
    """Raised when a directive status transition is not allowed by the state machine."""


class DirectiveStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"

    def transition_to(self, next_status: "DirectiveStatus") -> "DirectiveStatus":
        allowed = _VALID_TRANSITIONS.get(self.value, set())
        if next_status.value not in allowed:
            raise InvalidTransitionError(
                f"Invalid transition: {self.value!r} -> {next_status.value!r}. "
                f"Allowed from {self.value!r}: {sorted(allowed) or 'none'}"
            )
        return next_status


class DirectivePayload(ApexBase):
    type: DirectiveType
    parameters: dict[str, Any]
    description: str
    source_module: str

    @field_validator("parameters")
    @classmethod
    def parameters_must_not_be_empty(cls, v: dict) -> dict:
        if not v:
            raise ValueError("parameters must be a non-empty dict")
        return v

    @field_validator("source_module")
    @classmethod
    def source_module_must_be_valid(cls, v: str) -> str:
        allowed = {"spend_allocation", "paid_channels", "funnel", "onboarding"}
        if v not in allowed:
            raise ValueError(
                f"source_module must be one of {sorted(allowed)}, got {v!r}"
            )
        return v


class Directive(ApexBase):
    payload: DirectivePayload
    status: DirectiveStatus = DirectiveStatus.pending
    approved_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    kamino_job_id: Optional[str] = None
