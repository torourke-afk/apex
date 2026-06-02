"""Product & Experience API endpoints.

GET /api/product/pipeline          — product pipeline by stage with stage counts
GET /api/product/roadmap           — roadmap initiatives by quarter / theme
GET /api/product/testing-velocity  — A/B test velocity with baseline comparison
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.data.product_queries import (
    get_product_pipeline,
    get_product_roadmap,
    get_testing_velocity,
)

router = APIRouter(prefix="/api/product", tags=["product"])


# ---------------------------------------------------------------------------
# Response models — Pipeline
# ---------------------------------------------------------------------------

class PipelineItem(BaseModel):
    id: str
    name: str
    product_line: str
    stage: Literal["ideation", "discovery", "development", "testing", "launched"]
    owner: str
    target_date: str
    priority: Literal["critical", "high", "medium", "low"]
    confidence_score: float
    description: str


class PipelineResponse(BaseModel):
    items: list[PipelineItem]
    total: int
    stage_counts: dict[str, int]
    as_of: datetime


# ---------------------------------------------------------------------------
# Response models — Roadmap
# ---------------------------------------------------------------------------

class RoadmapItem(BaseModel):
    id: str
    initiative: str
    product_line: str
    quarter: str
    status: Literal["planned", "in_progress", "completed", "delayed"]
    priority: Literal["critical", "high", "medium", "low"]
    theme: Literal["acquisition", "retention", "engagement"]
    owner: str
    dependencies: list[str]
    kpi_target: str
    effort_weeks: int


class RoadmapResponse(BaseModel):
    items: list[RoadmapItem]
    total: int
    by_quarter: dict[str, list[str]]
    total_effort_weeks: int
    as_of: datetime


# ---------------------------------------------------------------------------
# Response models — Testing Velocity
# ---------------------------------------------------------------------------

class TestingVelocityResponse(BaseModel):
    period: str
    tests_run: int
    tests_won: int
    tests_inconclusive: int
    tests_lost: int
    win_rate: float
    avg_lift_pct: float
    avg_duration_days: float
    top_winning_test: str
    top_channel: str
    # Baseline comparison
    baseline_tests_run: int
    baseline_win_rate: float
    baseline_avg_lift_pct: float
    tests_run_delta: int
    tests_run_delta_pct: float
    win_rate_delta: float
    lift_delta: float
    as_of: datetime


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/pipeline", response_model=PipelineResponse)
def product_pipeline(
    stage: str | None = Query(
        default=None,
        description="Filter by stage: ideation|discovery|development|testing|launched",
    ),
    product_line: str | None = Query(
        default=None,
        description="Filter by product line: savings|checking|lending|investments|cards|digital|business",
    ),
):
    """Return product pipeline items with optional stage / product_line filters."""
    data = get_product_pipeline(stage=stage, product_line=product_line)
    return PipelineResponse(
        items=[PipelineItem(**item) for item in data["items"]],
        total=data["total"],
        stage_counts=data["stage_counts"],
        as_of=data["as_of"],
    )


@router.get("/roadmap", response_model=RoadmapResponse)
def product_roadmap(
    quarter: str | None = Query(
        default=None,
        description="Filter by quarter: Q1-2026|Q2-2026|Q3-2026|Q4-2026",
    ),
    product_line: str | None = Query(
        default=None,
        description="Filter by product line",
    ),
    theme: str | None = Query(
        default=None,
        description="Filter by theme: acquisition|retention|engagement",
    ),
):
    """Return roadmap initiatives with optional quarter / product_line / theme filters."""
    data = get_product_roadmap(quarter=quarter, product_line=product_line, theme=theme)
    return RoadmapResponse(
        items=[RoadmapItem(**item) for item in data["items"]],
        total=data["total"],
        by_quarter=data["by_quarter"],
        total_effort_weeks=data["total_effort_weeks"],
        as_of=data["as_of"],
    )


@router.get("/testing-velocity", response_model=TestingVelocityResponse)
def testing_velocity(
    period: Literal["30d", "60d", "90d"] = Query(
        default="30d",
        description="Look-back window: 30d | 60d | 90d",
    ),
):
    """Return A/B testing velocity metrics with baseline comparison.

    win_rate_delta and lift_delta show current vs. prior-period baseline,
    surfacing whether the team's experimentation cadence is improving.
    """
    data = get_testing_velocity(period=period)
    return TestingVelocityResponse(**data)
