"""Launch / Site Factory API endpoints.

GET   /api/launch/pipeline            — list all launch proposals with current stage
GET   /api/launch/pipeline/{id}       — single proposal detail with full stage history
POST  /api/launch/pipeline            — create a new launch proposal
POST  /api/launch/pipeline/{id}/advance — advance to next stage (with optional gate approval)
GET   /api/launch/pipeline/{id}/spec  — generated site spec for a proposal
GET   /api/launch/stats               — pipeline summary stats
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.services.launch import (
    ComplianceResult,
    LaunchProposal,
    PipelineStage,
    ProposalStatus,
    QAResult,
    SiteSpec,
    StageAdvanceError,
    StageRecord,
    advance_proposal,
    create_proposal,
    get_all_proposals,
    get_pipeline_stats,
    get_proposal,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/launch", tags=["launch"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CreateProposalRequest(BaseModel):
    """Body for creating a new launch proposal."""

    name: str = Field(description="Human-readable proposal name")
    persona: str = Field(description="Target persona slug, e.g. 'young-professional'")
    product: str = Field(description="Product slug, e.g. 'momentum-checking'")


class AdvanceRequest(BaseModel):
    """Body for advancing a proposal to its next stage."""

    gate_approved: bool = Field(
        default=False,
        description="Must be True when advancing past a human gate (APPROVE).",
    )


class StageRecordResponse(BaseModel):
    """A single stage record in the pipeline."""

    stage: str
    status: str
    entered_at: Optional[str] = None
    completed_at: Optional[str] = None
    notes: Optional[str] = None


class ProposalSummaryResponse(BaseModel):
    """Lightweight proposal for list views."""

    id: str
    name: str
    persona: str
    product: str
    status: str
    current_stage: str
    created_at: str
    updated_at: str


class ProposalDetailResponse(BaseModel):
    """Full proposal detail including stage history and results."""

    id: str
    name: str
    persona: str
    product: str
    status: str
    current_stage: str
    stages: list[StageRecordResponse]
    has_site_spec: bool
    compliance_results: Optional[dict] = None
    qa_results: Optional[dict] = None
    created_at: str
    updated_at: str


class PipelineStatsResponse(BaseModel):
    """Aggregate pipeline statistics."""

    total: int
    by_stage: dict[str, int]
    by_status: dict[str, int]
    avg_cycle_days: Optional[float]
    active: int
    completed: int
    human_gates_waiting: int


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _fmt_dt(dt) -> Optional[str]:
    """ISO-format a datetime, or None."""
    return dt.isoformat() if dt else None


def _stage_to_response(rec: StageRecord) -> StageRecordResponse:
    return StageRecordResponse(
        stage=rec.stage.value,
        status=rec.status.value,
        entered_at=_fmt_dt(rec.entered_at),
        completed_at=_fmt_dt(rec.completed_at),
        notes=rec.notes,
    )


def _proposal_summary(p: LaunchProposal) -> ProposalSummaryResponse:
    return ProposalSummaryResponse(
        id=p.id,
        name=p.name,
        persona=p.persona,
        product=p.product,
        status=p.status.value,
        current_stage=p.current_stage.value,
        created_at=_fmt_dt(p.created_at),
        updated_at=_fmt_dt(p.updated_at),
    )


def _proposal_detail(p: LaunchProposal) -> ProposalDetailResponse:
    return ProposalDetailResponse(
        id=p.id,
        name=p.name,
        persona=p.persona,
        product=p.product,
        status=p.status.value,
        current_stage=p.current_stage.value,
        stages=[_stage_to_response(s) for s in p.stages],
        has_site_spec=p.site_spec is not None,
        compliance_results=p.compliance_results.model_dump() if p.compliance_results else None,
        qa_results=p.qa_results.model_dump() if p.qa_results else None,
        created_at=_fmt_dt(p.created_at),
        updated_at=_fmt_dt(p.updated_at),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/pipeline", response_model=list[ProposalSummaryResponse])
def list_proposals():
    """List all launch proposals with their current stage."""
    try:
        proposals = get_all_proposals()
        return [_proposal_summary(p) for p in proposals]
    except Exception as exc:
        logger.exception("Failed to list launch proposals: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load pipeline data")


@router.get("/pipeline/{proposal_id}", response_model=ProposalDetailResponse)
def get_proposal_detail(proposal_id: str):
    """Return a single proposal with full stage history."""
    proposal = get_proposal(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail=f"Proposal '{proposal_id}' not found")
    return _proposal_detail(proposal)


@router.post("/pipeline", response_model=ProposalDetailResponse, status_code=201)
def create_new_proposal(body: CreateProposalRequest):
    """Create a new launch proposal.

    Generates a site spec from the given persona + product and starts the
    proposal at the RECOMMENDATION stage.
    """
    try:
        proposal = create_proposal(
            name=body.name,
            persona=body.persona,
            product=body.product,
        )
        return _proposal_detail(proposal)
    except Exception as exc:
        logger.exception("Failed to create proposal: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create proposal")


@router.post("/pipeline/{proposal_id}/advance", response_model=ProposalDetailResponse)
def advance_proposal_stage(proposal_id: str, body: AdvanceRequest):
    """Advance a proposal to its next pipeline stage.

    When the current stage is a human gate (APPROVE), ``gate_approved``
    must be ``True`` in the request body.
    """
    try:
        proposal = advance_proposal(proposal_id, gate_approved=body.gate_approved)
        return _proposal_detail(proposal)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Proposal '{proposal_id}' not found")
    except StageAdvanceError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to advance proposal %s: %s", proposal_id, exc)
        raise HTTPException(status_code=500, detail="Failed to advance proposal")


@router.get("/pipeline/{proposal_id}/spec")
def get_proposal_spec(proposal_id: str):
    """Return the generated site spec for a proposal."""
    proposal = get_proposal(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail=f"Proposal '{proposal_id}' not found")
    if proposal.site_spec is None:
        raise HTTPException(
            status_code=404,
            detail=f"Proposal '{proposal_id}' does not have a site spec yet",
        )
    return proposal.site_spec.model_dump()


@router.get("/stats", response_model=PipelineStatsResponse)
def pipeline_stats():
    """Return pipeline summary statistics."""
    try:
        stats = get_pipeline_stats()
        return PipelineStatsResponse(**stats)
    except Exception as exc:
        logger.exception("Failed to compute pipeline stats: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to compute stats")
