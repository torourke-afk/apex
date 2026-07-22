"""Product & Experience API endpoints.

GET /api/product/pipeline          — product pipeline by stage with stage counts
GET /api/product/roadmap           — roadmap initiatives by quarter / theme
GET /api/product/testing-velocity  — A/B test velocity with baseline comparison
GET /api/product/performance       — product line performance + conversion funnels
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
# Seed data — Product Performance
# ---------------------------------------------------------------------------

_PRODUCT_PERFORMANCE = [
    {
        "name": "Essential Checking",
        "funded": 6840,
        "cpihh": 278.0,
        "ltv": 3200.0,
        "margin": 0.38,
        "margin_status": "positive",
    },
    {
        "name": "Preferred Checking",
        "funded": 4120,
        "cpihh": 312.0,
        "ltv": 4800.0,
        "margin": 0.42,
        "margin_status": "positive",
    },
    {
        "name": "Money Market",
        "funded": 3280,
        "cpihh": 345.0,
        "ltv": 5100.0,
        "margin": 0.35,
        "margin_status": "positive",
    },
    {
        "name": "Certificate of Deposit",
        "funded": 2460,
        "cpihh": 298.0,
        "ltv": 4200.0,
        "margin": 0.31,
        "margin_status": "warning",
    },
    {
        "name": "Savings Builder",
        "funded": 1720,
        "cpihh": 256.0,
        "ltv": 2800.0,
        "margin": 0.28,
        "margin_status": "warning",
    },
]

_CONV_FUNNELS = [
    {
        "name": "Essential Checking",
        "stages": [
            {"label": "Visit", "volume": "482K", "pct": 100},
            {"label": "Start App", "volume": "38.6K", "pct": 42},
            {"label": "Complete", "volume": "24.1K", "pct": 26},
            {"label": "Funded", "volume": "6,840", "pct": 8},
        ],
    },
    {
        "name": "Preferred Checking",
        "stages": [
            {"label": "Visit", "volume": "310K", "pct": 100},
            {"label": "Start App", "volume": "24.8K", "pct": 38},
            {"label": "Complete", "volume": "14.9K", "pct": 23},
            {"label": "Funded", "volume": "4,120", "pct": 6},
        ],
    },
    {
        "name": "Money Market",
        "stages": [
            {"label": "Visit", "volume": "228K", "pct": 100},
            {"label": "Start App", "volume": "16.0K", "pct": 35},
            {"label": "Complete", "volume": "10.2K", "pct": 22},
            {"label": "Funded", "volume": "3,280", "pct": 7},
        ],
    },
]


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
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    product: str | None = Query(default=None, description="Comma-separated product filter"),
    dma: str | None = Query(default=None, description="Comma-separated DMA filter"),
    channel: str | None = Query(default=None, description="Comma-separated channel filter"),
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
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    product: str | None = Query(default=None, description="Comma-separated product filter"),
    dma: str | None = Query(default=None, description="Comma-separated DMA filter"),
    channel: str | None = Query(default=None, description="Comma-separated channel filter"),
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
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    product: str | None = Query(default=None, description="Comma-separated product filter"),
    dma: str | None = Query(default=None, description="Comma-separated DMA filter"),
    channel: str | None = Query(default=None, description="Comma-separated channel filter"),
):
    """Return A/B testing velocity metrics with baseline comparison.

    win_rate_delta and lift_delta show current vs. prior-period baseline,
    surfacing whether the team's experimentation cadence is improving.
    """
    data = get_testing_velocity(period=period)
    return TestingVelocityResponse(**data)


@router.get("/performance")
def product_performance(
    product: str | None = Query(
        default=None,
        description="Filter by product name (case-insensitive substring match)",
    ),
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    dma: str | None = Query(default=None, description="Comma-separated DMA filter"),
    channel: str | None = Query(default=None, description="Comma-separated channel filter"),
):
    """Return product line performance data with conversion funnels.

    Each product includes funded count, CPIHH, LTV, margin, and margin
    status.  ``conv_funnels`` provides per-product funnel stage breakdowns
    where available.  Use the ``product`` query param to filter by name.
    """
    products = list(_PRODUCT_PERFORMANCE)
    funnels = list(_CONV_FUNNELS)

    if product:
        needle = product.lower()
        products = [p for p in products if needle in p["name"].lower()]
        funnels = [f for f in funnels if needle in f["name"].lower()]

    return {
        "products": products,
        "conv_funnels": funnels,
        "count": len(products),
    }
