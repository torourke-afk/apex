"""Ops REST API.

GET  /api/ops/calendar           — Marketing operations calendar
GET  /api/ops/capacity           — Team / resource capacity by channel
GET  /api/ops/approvals          — List approval requests (Directives of type "approval")
POST /api/ops/approvals/{id}/approve — Approve a pending request
POST /api/ops/approvals/{id}/reject  — Reject a pending request
GET  /api/ops/health             — System health status
GET  /api/ops/competitive-feed   — Latest competitive intelligence items
"""

from __future__ import annotations

import uuid
from datetime import datetime, date, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.data.database import get_session
from src.data.orm import Directive as DirectiveORM
from src.data.ops_queries import (
    get_ops_calendar,
    get_ops_capacity,
    get_ops_health,
    get_competitive_feed,
)

router = APIRouter(prefix="/api/ops", tags=["ops"])


# ---------------------------------------------------------------------------
# Response models — Calendar
# ---------------------------------------------------------------------------

class CalendarEvent(BaseModel):
    id: str
    title: str
    event_type: str
    date: str
    channel: str
    owner: str
    status: str
    description: str


class CalendarResponse(BaseModel):
    events: list[CalendarEvent]
    total: int
    as_of: datetime


# ---------------------------------------------------------------------------
# Response models — Capacity
# ---------------------------------------------------------------------------

class CapacityItem(BaseModel):
    id: str
    team: str
    channel: str
    period: str
    allocated_hours: int
    used_hours: int
    available_hours: int
    utilization_pct: float
    projects: list[str]


class CapacitySummary(BaseModel):
    total: int
    total_allocated_hours: int
    total_used_hours: int
    avg_utilization_pct: float


class CapacityResponse(BaseModel):
    members: list[CapacityItem]
    summary: CapacitySummary
    as_of: datetime


# ---------------------------------------------------------------------------
# Response models — Approvals
# ---------------------------------------------------------------------------

class ApprovalResponse(BaseModel):
    id: uuid.UUID
    title: str
    approval_type: str
    priority: str
    owner: str
    due_date: Optional[date]
    status: str
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_row(cls, row: DirectiveORM) -> "ApprovalResponse":
        return cls(
            id=row.id,
            title=row.title,
            approval_type=row.directive_type,
            priority=row.priority,
            owner=row.owner,
            due_date=row.due_date,
            status=row.status,
            notes=row.notes,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class ApprovalsListResponse(BaseModel):
    items: list[ApprovalResponse]
    count: int


class ApproveRejectRequest(BaseModel):
    comment: Optional[str] = None


class ApproveRejectResponse(BaseModel):
    success: bool
    message: str


# ---------------------------------------------------------------------------
# Response models — Health
# ---------------------------------------------------------------------------

class HealthSystem(BaseModel):
    status: str
    last_checked: str
    message: str


class HealthResponse(BaseModel):
    overall_status: str
    systems: dict[str, HealthSystem]
    as_of: datetime


# ---------------------------------------------------------------------------
# Response models — Competitive Feed
# ---------------------------------------------------------------------------

class CompetitiveFeedItem(BaseModel):
    id: str
    competitor: str
    category: str
    headline: str
    summary: str
    source: str
    detected_at: str
    impact: str
    tags: list[str]


class CompetitiveFeedResponse(BaseModel):
    items: list[CompetitiveFeedItem]
    total: int
    as_of: datetime


# ---------------------------------------------------------------------------
# Approval seed helper
# ---------------------------------------------------------------------------

_APPROVAL_SEEDS = [
    {
        "title": "Q2 SEM Budget Increase (+$150K)",
        "directive_type": "budget_increase",
        "priority": "high",
        "owner": "Media - Paid Search",
        "notes": "Competitor share of voice shift warrants incremental Q2 investment.",
        "status": "pending",
    },
    {
        "title": "Mortgage Campaign Brief Approval",
        "directive_type": "campaign_brief",
        "priority": "medium",
        "owner": "Creative - Lending",
        "notes": "Final brief for Q2 mortgage display and OTT creative assets.",
        "status": "pending",
    },
    {
        "title": "Paid Social Creative Asset Sign-off",
        "directive_type": "creative_asset",
        "priority": "medium",
        "owner": "Media - Paid Social",
        "notes": "Three-cell creative rotation for May checking account campaign.",
        "status": "pending",
    },
    {
        "title": "Q3 Channel Plan — Digital",
        "directive_type": "channel_plan",
        "priority": "low",
        "owner": "Analytics",
        "notes": "Draft Q3 media mix recommendation pending CMO review.",
        "status": "pending",
    },
]


def _seed_approvals(db: Session) -> None:
    """Insert seed approval directives if none exist yet."""
    from datetime import date as date_type

    existing = (
        db.query(DirectiveORM)
        .filter(DirectiveORM.directive_type.in_(
            ["budget_increase", "campaign_brief", "creative_asset", "channel_plan"]
        ))
        .first()
    )
    if existing is not None:
        return

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for seed in _APPROVAL_SEEDS:
        row = DirectiveORM(
            id=uuid.uuid4(),
            title=seed["title"],
            directive_type=seed["directive_type"],
            priority=seed["priority"],
            owner=seed["owner"],
            notes=seed["notes"],
            status=seed["status"],
            due_date=date_type(2026, 5, 20),
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    db.commit()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/calendar", response_model=CalendarResponse)
def ops_calendar(
    month: Optional[str] = Query(
        default=None,
        description="Filter by month (YYYY-MM), e.g. 2026-05",
    ),
    channel: Optional[str] = Query(
        default=None,
        description="Filter by channel: sem|paid_social|seo|display|llm|all",
    ),
    event_type: Optional[str] = Query(
        default=None,
        description="Filter by type: campaign_launch|creative_review|deadline|review|planning",
    ),
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    product: str | None = Query(default=None, description="Comma-separated product filter"),
    dma: str | None = Query(default=None, description="Comma-separated DMA filter"),
):
    """Return marketing operations calendar events."""
    data = get_ops_calendar(month=month, channel=channel, event_type=event_type)
    return CalendarResponse(
        events=[CalendarEvent(**item) for item in data["items"]],
        total=data["total"],
        as_of=data["as_of"],
    )


@router.get("/capacity", response_model=CapacityResponse)
def ops_capacity(
    period: Optional[str] = Query(
        default=None,
        description="Filter by period (YYYY-MM), e.g. 2026-05",
    ),
    channel: Optional[str] = Query(
        default=None,
        description="Filter by channel: sem|paid_social|seo|display|llm|all",
    ),
    team: Optional[str] = Query(
        default=None,
        description="Partial team name search (case-insensitive)",
    ),
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    product: str | None = Query(default=None, description="Comma-separated product filter"),
    dma: str | None = Query(default=None, description="Comma-separated DMA filter"),
):
    """Return team resource capacity with utilization metrics."""
    data = get_ops_capacity(period=period, channel=channel, team=team)
    return CapacityResponse(
        members=[CapacityItem(**item) for item in data["items"]],
        summary=CapacitySummary(
            total=data["total"],
            total_allocated_hours=data["total_allocated_hours"],
            total_used_hours=data["total_used_hours"],
            avg_utilization_pct=data["avg_utilization_pct"],
        ),
        as_of=data["as_of"],
    )


@router.get("/approvals", response_model=ApprovalsListResponse)
def list_approvals(
    status: Optional[str] = Query(
        default=None,
        description="Filter by status: pending|approved|rejected",
    ),
    priority: Optional[str] = Query(
        default=None,
        description="Filter by priority: critical|high|medium|low",
    ),
    db: Session = Depends(get_session),
):
    """Return approval requests, seeding demo records when the table is empty."""
    _seed_approvals(db)

    approval_types = ["budget_increase", "campaign_brief", "creative_asset", "channel_plan"]
    query = db.query(DirectiveORM).filter(
        DirectiveORM.directive_type.in_(approval_types)
    )
    if status:
        query = query.filter(DirectiveORM.status == status)
    if priority:
        query = query.filter(DirectiveORM.priority == priority)

    rows = query.order_by(DirectiveORM.created_at.desc()).all()
    items = [ApprovalResponse.from_orm_row(r) for r in rows]
    return ApprovalsListResponse(items=items, count=len(items))


@router.post("/approvals/{approval_id}/approve", response_model=ApproveRejectResponse)
def approve_approval(
    approval_id: uuid.UUID,
    body: ApproveRejectRequest = ApproveRejectRequest(),
    db: Session = Depends(get_session),
):
    """Mark an approval request as approved."""
    approval_types = ["budget_increase", "campaign_brief", "creative_asset", "channel_plan"]
    row = (
        db.query(DirectiveORM)
        .filter(
            DirectiveORM.id == approval_id,
            DirectiveORM.directive_type.in_(approval_types),
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Approval not found")

    row.status = "approved"
    if body.comment:
        existing = row.notes or ""
        row.notes = f"{existing}\n[Approved] {body.comment}".strip()
    row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(row)
    return ApproveRejectResponse(success=True, message=f"Approval '{row.title}' approved successfully.")


@router.post("/approvals/{approval_id}/reject", response_model=ApproveRejectResponse)
def reject_approval(
    approval_id: uuid.UUID,
    body: ApproveRejectRequest = ApproveRejectRequest(),
    db: Session = Depends(get_session),
):
    """Mark an approval request as rejected."""
    approval_types = ["budget_increase", "campaign_brief", "creative_asset", "channel_plan"]
    row = (
        db.query(DirectiveORM)
        .filter(
            DirectiveORM.id == approval_id,
            DirectiveORM.directive_type.in_(approval_types),
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Approval not found")

    row.status = "rejected"
    if body.comment:
        existing = row.notes or ""
        row.notes = f"{existing}\n[Rejected] {body.comment}".strip()
    row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(row)
    return ApproveRejectResponse(success=True, message=f"Approval '{row.title}' rejected.")


@router.get("/health", response_model=HealthResponse)
def ops_health(
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    product: str | None = Query(default=None, description="Comma-separated product filter"),
    dma: str | None = Query(default=None, description="Comma-separated DMA filter"),
    channel: str | None = Query(default=None, description="Comma-separated channel filter"),
):
    """Return system health status across all components."""
    data = get_ops_health()
    systems = {
        c["name"]: HealthSystem(status=c["status"], last_checked=c["last_checked"], message=c["message"])
        for c in data["components"]
    }
    return HealthResponse(
        overall_status=data["overall_status"],
        systems=systems,
        as_of=data["as_of"],
    )


@router.get("/competitive-feed", response_model=CompetitiveFeedResponse)
def competitive_feed(
    competitor: Optional[str] = Query(
        default=None,
        description="Filter by competitor name (partial match)",
    ),
    category: Optional[str] = Query(
        default=None,
        description="Filter by category: pricing|product|campaign|channel|promotion",
    ),
    impact: Optional[str] = Query(
        default=None,
        description="Filter by impact level: high|medium|low",
    ),
    limit: int = Query(default=20, ge=1, le=100),
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    product: str | None = Query(default=None, description="Comma-separated product filter"),
    dma: str | None = Query(default=None, description="Comma-separated DMA filter"),
    channel: str | None = Query(default=None, description="Comma-separated channel filter"),
):
    """Return latest competitive intelligence feed items."""
    data = get_competitive_feed(
        competitor=competitor,
        category=category,
        impact=impact,
        limit=limit,
    )
    return CompetitiveFeedResponse(
        items=[CompetitiveFeedItem(**item) for item in data["items"]],
        total=data["total"],
        as_of=data["as_of"],
    )
