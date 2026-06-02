"""Directives REST API.

POST  /api/directives                 — Submit a new directive
GET   /api/directives                 — List directives, filterable by status/directive_type/owner
GET   /api/directives/{id}            — Directive detail
PATCH /api/directives/{id}/cancel     — Cancel a directive
GET   /api/directives/{id}/status     — Get directive status
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.data.database import get_session
from src.data.orm import Directive as DirectiveORM
from src.kamino.events import DirectiveEvent, publish_directive_event
from src.kamino.models import DirectivePayload, DirectiveStatus, InvalidTransitionError

router = APIRouter(prefix="/api/directives", tags=["directives"])

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

_VALID_TYPES = {"strategic", "tactical", "operational"}
_VALID_PRIORITIES = {"high", "medium", "low"}


class CreateDirectiveRequest(BaseModel):
    title: str
    directive_type: str  # "strategic" | "tactical" | "operational"
    priority: str = "medium"  # "high" | "medium" | "low"
    owner: str
    due_date: Optional[date] = None
    status: DirectiveStatus = DirectiveStatus.pending
    payload: Optional[DirectivePayload] = None
    notes: Optional[str] = None


class DirectiveResponse(BaseModel):
    id: uuid.UUID
    title: str
    directive_type: str
    priority: str
    owner: str
    due_date: Optional[date]
    status: str
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_row(cls, row: DirectiveORM) -> "DirectiveResponse":
        return cls(
            id=row.id,
            title=row.title,
            directive_type=row.directive_type,
            priority=row.priority,
            owner=row.owner,
            due_date=row.due_date,
            status=row.status,
            notes=row.notes,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class DirectiveStatusResponse(BaseModel):
    id: uuid.UUID
    status: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=DirectiveResponse, status_code=201)
def submit_directive(body: CreateDirectiveRequest, db: Session = Depends(get_session)):
    """Submit a new directive."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    row = DirectiveORM(
        id=uuid.uuid4(),
        title=body.title,
        directive_type=body.directive_type,
        priority=body.priority,
        owner=body.owner,
        due_date=body.due_date,
        status=body.status.value,
        notes=body.notes,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    publish_directive_event(
        DirectiveEvent(
            directive_id=row.id,
            event_type="created",
            status=row.status,
            occurred_at=row.created_at,
            title=row.title,
            owner=row.owner,
        )
    )
    return DirectiveResponse.from_orm_row(row)


@router.get("", response_model=list[DirectiveResponse])
def list_directives(
    status: Optional[str] = Query(default=None, description="Filter by status"),
    directive_type: Optional[str] = Query(default=None, description="Filter by directive_type"),
    owner: Optional[str] = Query(default=None, description="Filter by owner"),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_session),
):
    """Return directives ordered by created_at desc."""
    query = db.query(DirectiveORM)
    if status:
        query = query.filter(DirectiveORM.status == status)
    if directive_type:
        query = query.filter(DirectiveORM.directive_type == directive_type)
    if owner:
        query = query.filter(DirectiveORM.owner == owner)
    rows = query.order_by(DirectiveORM.created_at.desc()).limit(limit).all()
    return [DirectiveResponse.from_orm_row(r) for r in rows]


@router.get("/{directive_id}", response_model=DirectiveResponse)
def get_directive(directive_id: uuid.UUID, db: Session = Depends(get_session)):
    """Return a single directive by ID."""
    row = db.query(DirectiveORM).filter(DirectiveORM.id == directive_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Directive not found")
    return DirectiveResponse.from_orm_row(row)


@router.patch("/{directive_id}/cancel", response_model=DirectiveResponse)
def cancel_directive(directive_id: uuid.UUID, db: Session = Depends(get_session)):
    """Cancel a directive using the state machine."""
    row = db.query(DirectiveORM).filter(DirectiveORM.id == directive_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Directive not found")

    try:
        current = DirectiveStatus(row.status)
    except ValueError:
        raise HTTPException(
            status_code=409,
            detail=f"Directive has unrecognised status {row.status!r}; cannot cancel",
        )

    if current == DirectiveStatus.cancelled:
        return DirectiveResponse.from_orm_row(row)

    try:
        current.transition_to(DirectiveStatus.cancelled)
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    row.status = DirectiveStatus.cancelled.value
    row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(row)
    publish_directive_event(
        DirectiveEvent(
            directive_id=row.id,
            event_type="cancelled",
            status=row.status,
            occurred_at=row.updated_at,
            title=row.title,
            owner=row.owner,
        )
    )
    return DirectiveResponse.from_orm_row(row)


@router.get("/{directive_id}/status", response_model=DirectiveStatusResponse)
def get_directive_status(directive_id: uuid.UUID, db: Session = Depends(get_session)):
    """Return just the status of a directive."""
    row = db.query(DirectiveORM).filter(DirectiveORM.id == directive_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Directive not found")
    return DirectiveStatusResponse(id=row.id, status=row.status)
