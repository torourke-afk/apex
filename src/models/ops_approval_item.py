"""ApprovalItem — Operations Command Center approval workflow model.

Tracks creative approvals, budget change requests, compliance sign-offs,
and other items moving through the ops approval queue.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import Field

from src.models.base import ApexBase


class ApprovalCategory(str, Enum):
    CREATIVE = "creative"
    BUDGET_CHANGE = "budget_change"
    COMPLIANCE = "compliance"
    VENDOR_CONTRACT = "vendor_contract"
    CAMPAIGN_BRIEF = "campaign_brief"
    OTHER = "other"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class ApprovalPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ApprovalItem(ApexBase):
    """An item in the ops approval queue."""

    title: str = Field(min_length=1, max_length=255, description="Approval request title")
    category: ApprovalCategory
    status: ApprovalStatus = ApprovalStatus.PENDING
    priority: ApprovalPriority = ApprovalPriority.MEDIUM

    requestor: str = Field(min_length=1, description="Person who submitted the request")
    approver: Optional[str] = Field(default=None, description="Assigned approver")
    due_date: Optional[datetime] = Field(default=None, description="Approval deadline (UTC)")
    resolved_at: Optional[datetime] = Field(default=None, description="When approved/rejected")

    budget_impact: Optional[Decimal] = Field(
        default=None,
        description="Dollar impact of this approval (positive = spend increase)",
    )
    notes: Optional[str] = Field(default=None, description="Review notes or rejection reason")
    artifact_url: Optional[str] = Field(
        default=None, description="Link to the item being approved (brief, creative, etc.)"
    )
