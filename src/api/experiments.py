"""Experiments API endpoints.

GET  /api/experiments           — list all experiments with summary stats
GET  /api/experiments/summary   — aggregate stats (total, running, win_rate, avg_lift)
GET  /api/experiments/{id}      — single experiment with full variant data and results
POST /api/experiments           — create a new experiment (draft)
POST /api/experiments/{id}/analyze   — run statistical analysis on current data
GET  /api/experiments/{id}/sequential — O'Brien-Fleming boundaries and current position
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, Field

from ..services.experiments import (
    ExperimentStatus,
    analyze_experiment,
    compute_lift,
    create_experiment,
    get_experiment,
    get_summary,
    list_experiments,
    obrien_fleming_boundaries,
    power_analysis,
    two_proportion_z_test,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class VariantInput(BaseModel):
    name: str = Field(description="Display name for this variant")
    traffic_pct: float = Field(
        default=0.5, ge=0, le=1, description="Traffic allocation fraction (0-1)"
    )
    visitors: int = Field(default=0, ge=0, description="Initial visitor count")
    conversions: int = Field(default=0, ge=0, description="Initial conversion count")


class CreateExperimentRequest(BaseModel):
    name: str = Field(description="Experiment name")
    hypothesis: str = Field(description="What you expect to happen and why")
    metric: str = Field(description="Primary KPI to measure")
    variants: list[VariantInput] = Field(
        min_length=2, description="At least 2 variants (control + treatment)"
    )


class VariantResponse(BaseModel):
    name: str
    traffic_pct: float
    visitors: int
    conversions: int
    conversion_rate: float


class ResultsResponse(BaseModel):
    winner: str | None = None
    lift: float | None = None
    lift_ci_lower: float | None = None
    lift_ci_upper: float | None = None
    z_stat: float | None = None
    p_value: float | None = None
    confidence_level: float | None = None
    is_significant: bool = False
    power: float | None = None
    underpowered: bool = False


class ExperimentResponse(BaseModel):
    id: str
    name: str
    hypothesis: str
    metric: str
    status: str
    variants: list[VariantResponse]
    start_date: str | None = None
    end_date: str | None = None
    planned_sample: int = 0
    results: ResultsResponse | None = None


class ExperimentSummaryResponse(BaseModel):
    id: str
    name: str
    metric: str
    status: str
    variant_count: int
    total_visitors: int
    winner: str | None = None
    lift: float | None = None
    is_significant: bool = False


class SequentialBoundary(BaseModel):
    analysis_number: int
    information_fraction: float
    sample_size: int
    z_boundary: float
    p_value_boundary: float
    label: str


class SequentialResponse(BaseModel):
    experiment_id: str
    experiment_name: str
    planned_sample: int
    current_sample: int
    current_fraction: float
    boundaries: list[SequentialBoundary]
    current_z: float | None = None
    crossed_boundary: bool = False
    recommendation: str


class AggregateStatsResponse(BaseModel):
    total: int
    running: int
    completed: int
    drafts: int
    win_rate: float
    avg_lift: float


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _experiment_to_response(exp: Any) -> ExperimentResponse:
    """Convert a service-layer Experiment dataclass to the API response model."""
    variants = [
        VariantResponse(
            name=v.name,
            traffic_pct=v.traffic_pct,
            visitors=v.visitors,
            conversions=v.conversions,
            conversion_rate=round(v.conversion_rate, 6),
        )
        for v in exp.variants
    ]

    results = None
    if exp.results is not None:
        results = ResultsResponse(
            winner=exp.results.winner,
            lift=exp.results.lift,
            lift_ci_lower=exp.results.lift_ci_lower,
            lift_ci_upper=exp.results.lift_ci_upper,
            z_stat=exp.results.z_stat,
            p_value=exp.results.p_value,
            confidence_level=exp.results.confidence_level,
            is_significant=exp.results.is_significant,
            power=exp.results.power,
            underpowered=exp.results.underpowered,
        )

    return ExperimentResponse(
        id=exp.id,
        name=exp.name,
        hypothesis=exp.hypothesis,
        metric=exp.metric,
        status=exp.status.value,
        variants=variants,
        start_date=exp.start_date,
        end_date=exp.end_date,
        planned_sample=exp.planned_sample,
        results=results,
    )


def _experiment_to_summary(exp: Any) -> ExperimentSummaryResponse:
    """Convert to a lightweight summary row."""
    total_visitors = sum(v.visitors for v in exp.variants)
    return ExperimentSummaryResponse(
        id=exp.id,
        name=exp.name,
        metric=exp.metric,
        status=exp.status.value,
        variant_count=len(exp.variants),
        total_visitors=total_visitors,
        winner=exp.results.winner if exp.results else None,
        lift=exp.results.lift if exp.results else None,
        is_significant=exp.results.is_significant if exp.results else False,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=AggregateStatsResponse)
def experiments_summary():
    """Aggregate stats: total, running, win_rate, avg_lift."""
    try:
        return get_summary()
    except Exception as exc:
        logger.warning("experiments_summary fallback: %s", exc)
        return AggregateStatsResponse(
            total=0, running=0, completed=0, drafts=0, win_rate=0.0, avg_lift=0.0
        )


@router.get("", response_model=list[ExperimentSummaryResponse])
def experiments_list(
    status: str | None = Query(
        default=None, description="Filter by status: draft, running, paused, completed, archived"
    ),
):
    """List all experiments with summary stats."""
    try:
        experiments = list_experiments()

        if status:
            status_values = [s.strip().lower() for s in status.split(",")]
            experiments = [e for e in experiments if e.status.value in status_values]

        return [_experiment_to_summary(e) for e in experiments]
    except Exception as exc:
        logger.warning("experiments_list fallback: %s", exc)
        return []


@router.get("/{experiment_id}", response_model=ExperimentResponse)
def experiments_detail(
    experiment_id: str = Path(description="Experiment ID"),
):
    """Single experiment with full variant data and results."""
    exp = get_experiment(experiment_id)
    if exp is None:
        raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found")
    return _experiment_to_response(exp)


@router.post("", response_model=ExperimentResponse, status_code=201)
def experiments_create(body: CreateExperimentRequest):
    """Create a new experiment in draft status."""
    try:
        exp = create_experiment(
            name=body.name,
            hypothesis=body.hypothesis,
            metric=body.metric,
            variants=[v.model_dump() for v in body.variants],
        )
        return _experiment_to_response(exp)
    except Exception as exc:
        logger.error("experiments_create error: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{experiment_id}/analyze", response_model=ExperimentResponse)
def experiments_analyze(
    experiment_id: str = Path(description="Experiment ID"),
    alpha: float = Query(default=0.05, gt=0, lt=1, description="Significance level"),
):
    """Run statistical analysis on current experiment data."""
    exp = analyze_experiment(experiment_id, alpha=alpha)
    if exp is None:
        raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found")
    return _experiment_to_response(exp)


@router.get("/{experiment_id}/sequential", response_model=SequentialResponse)
def experiments_sequential(
    experiment_id: str = Path(description="Experiment ID"),
    alpha: float = Query(default=0.05, gt=0, lt=1, description="Significance level"),
    n_analyses: int = Query(default=4, ge=2, le=10, description="Number of planned interim analyses"),
):
    """O'Brien-Fleming sequential boundaries and current position."""
    exp = get_experiment(experiment_id)
    if exp is None:
        raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found")

    if exp.planned_sample <= 0:
        raise HTTPException(
            status_code=400,
            detail="Experiment has no planned sample size; cannot compute sequential boundaries",
        )

    # Compute boundaries
    boundaries_raw = obrien_fleming_boundaries(
        planned_sample=exp.planned_sample,
        alpha=alpha,
        n_analyses=n_analyses,
    )
    boundaries = [SequentialBoundary(**b) for b in boundaries_raw]

    # Current state
    current_sample = sum(v.visitors for v in exp.variants)
    current_fraction = round(current_sample / exp.planned_sample, 4) if exp.planned_sample > 0 else 0.0

    # Current z-stat from results (if computed)
    current_z: float | None = None
    crossed = False
    if exp.results and exp.results.z_stat is not None:
        current_z = exp.results.z_stat
        # Check if current z crosses the boundary at the nearest analysis point
        for b in boundaries:
            if current_fraction <= b.information_fraction:
                crossed = abs(current_z) >= b.z_boundary
                break
        else:
            # Past the last boundary — use final boundary
            if boundaries:
                crossed = abs(current_z) >= boundaries[-1].z_boundary

    # Recommendation
    if exp.status == ExperimentStatus.DRAFT:
        recommendation = "Experiment has not started. Launch to begin collecting data."
    elif current_sample == 0:
        recommendation = "No data collected yet. Continue running the experiment."
    elif crossed:
        recommendation = (
            "Current test statistic crosses the sequential boundary. "
            "Consider stopping early — the result is significant at this interim look."
        )
    elif current_fraction < 0.25:
        recommendation = (
            f"Only {current_fraction:.0%} of planned sample collected. "
            "Too early for reliable inference. Continue running."
        )
    elif current_fraction >= 1.0:
        if exp.results and exp.results.is_significant:
            recommendation = "Full sample collected. Result is statistically significant."
        else:
            recommendation = (
                "Full sample collected. Result is not statistically significant. "
                "Consider increasing sample size or accepting the null."
            )
    else:
        recommendation = (
            f"{current_fraction:.0%} of planned sample collected. "
            "Test statistic has not crossed the O'Brien-Fleming boundary. Continue running."
        )

    return SequentialResponse(
        experiment_id=exp.id,
        experiment_name=exp.name,
        planned_sample=exp.planned_sample,
        current_sample=current_sample,
        current_fraction=current_fraction,
        boundaries=boundaries,
        current_z=current_z,
        crossed_boundary=crossed,
        recommendation=recommendation,
    )
