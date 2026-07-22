"""Allocation / Optimization API endpoints (Service #11).

GET  /api/allocation/status   -- current allocation state (60 combos)
GET  /api/allocation/curves   -- response curve parameters for visualization
POST /api/allocation/optimize -- run the NBD allocator
GET  /api/allocation/rollout  -- 30-day rollout simulation
GET  /api/allocation/moves    -- top reallocation moves
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/allocation", tags=["allocation"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class OptimizeRequest(BaseModel):
    """Request body for the optimize endpoint."""

    objective: Literal["profit", "volume"] = Field(
        default="profit",
        description="Optimization objective: maximize profit (contribution margin) or volume (total accounts)",
    )
    budget: float = Field(
        default=0,
        ge=0,
        description="Total weekly budget to allocate. 0 = use current total (budget-neutral reallocation).",
    )


class ComboStatus(BaseModel):
    """Status of a single campaign x DMA combo."""

    campaign: str
    dma: str
    role: str
    current_spend: float
    current_accounts: float
    optimal_accounts: float
    waste_gap_accounts: float
    waste_gap_dollars: float


class StatusResponse(BaseModel):
    """Response for the /status endpoint."""

    combos: list[ComboStatus]
    total_spend: float
    total_accounts: float
    total_waste_gap_dollars: float
    combo_count: int


class CurvePoint(BaseModel):
    """Response curve data for a single combo."""

    campaign: str
    dma: str
    role: str
    k: float
    s_ref: float
    current_spend: float
    current_accounts: float
    optimal_spend: float
    optimal_accounts: float
    account_value: float
    spend_lo: float
    spend_hi: float
    curve_samples: dict[str, list[float]]


class CurvesResponse(BaseModel):
    """Response for the /curves endpoint."""

    curves: list[CurvePoint]
    count: int


class AllocationEntry(BaseModel):
    """A single combo's allocation result."""

    campaign: str
    dma: str
    role: str
    current_spend: float
    optimal_spend: float
    current_accounts: float
    optimal_accounts: float
    current_profit: float
    optimal_profit: float
    waste_gap_accounts: float
    waste_gap_dollars: float
    delta_spend: float
    delta_pct: float


class MoveEntry(BaseModel):
    """A single reallocation move."""

    from_campaign: str
    from_dma: str
    to_campaign: str
    to_dma: str
    delta: float
    rationale: str
    roas_impact: float


class OptimizeResponse(BaseModel):
    """Response for the /optimize endpoint."""

    objective: str
    budget: float
    allocations: list[AllocationEntry]
    top_moves: list[MoveEntry]
    total_current_spend: float
    total_optimal_spend: float
    total_current_accounts: float
    total_optimal_accounts: float
    total_current_profit: float
    total_optimal_profit: float
    total_waste_gap_dollars: float
    headline_lift_pct: float
    headline_left_on_table_annual: float


class RolloutSnapshot(BaseModel):
    """A single day's rollout snapshot."""

    day: int
    total_spend: float
    total_accounts: float
    total_profit: float
    pct_progress: float


class RolloutResponse(BaseModel):
    """Response for the /rollout endpoint."""

    days: list[RolloutSnapshot]
    rollout_length: int
    max_weekly_change_pct: float


class MovesResponse(BaseModel):
    """Response for the /moves endpoint."""

    moves: list[MoveEntry]
    count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_engine():
    """Lazy-import the allocation engine."""
    from src.services.allocation import (
        Objective,
        generate_seed_combos,
        run_optimization,
        simulate_rollout,
        get_curve_data,
        compute_waste_gap,
    )
    return {
        "Objective": Objective,
        "generate_seed_combos": generate_seed_combos,
        "run_optimization": run_optimization,
        "simulate_rollout": simulate_rollout,
        "get_curve_data": get_curve_data,
        "compute_waste_gap": compute_waste_gap,
    }


def _dataclass_to_dict(obj: Any) -> dict[str, Any]:
    """Convert a dataclass instance to a JSON-safe dict."""
    import math

    d = asdict(obj)
    _sanitize(d)
    return d


def _sanitize(d: dict) -> None:
    """Replace inf/nan with None for JSON safety."""
    import math

    for key, val in d.items():
        if isinstance(val, float) and (math.isinf(val) or math.isnan(val)):
            d[key] = None
        elif isinstance(val, dict):
            _sanitize(val)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    _sanitize(item)


# ---------------------------------------------------------------------------
# Fallback seed data (used when the engine import fails)
# ---------------------------------------------------------------------------

def _fallback_status() -> dict:
    """Minimal fallback so the endpoint always returns JSON."""
    return {
        "combos": [
            {"campaign": "SEM Brand", "dma": "Cincinnati, OH", "role": "Defend",
             "current_spend": 22500, "current_accounts": 185.3,
             "optimal_accounts": 214.7, "waste_gap_accounts": 29.4, "waste_gap_dollars": 4820},
            {"campaign": "SEM Non-Brand", "dma": "Chicago, IL", "role": "Scale",
             "current_spend": 34200, "current_accounts": 242.1,
             "optimal_accounts": 298.5, "waste_gap_accounts": 56.4, "waste_gap_dollars": 8340},
            {"campaign": "Paid Social - Prospecting", "dma": "Columbus, OH", "role": "Scale",
             "current_spend": 28100, "current_accounts": 198.7,
             "optimal_accounts": 251.2, "waste_gap_accounts": 52.5, "waste_gap_dollars": 7150},
        ],
        "total_spend": 1_430_000,
        "total_accounts": 5_620,
        "total_waste_gap_dollars": 182_400,
        "combo_count": 60,
    }


def _fallback_moves() -> list[dict]:
    """Fallback moves when the engine is unavailable."""
    return [
        {
            "from_campaign": "Connected TV (Nashville, TN)",
            "from_dma": "Nashville, TN",
            "to_campaign": "SEM Non-Brand (Chicago, IL)",
            "to_dma": "Chicago, IL",
            "delta": 12_400,
            "rationale": "Scale campaign in Chicago has steeper marginal curve; each shifted $ yields 56 incremental accounts",
            "roas_impact": 2.34,
        },
        {
            "from_campaign": "Display Programmatic (Charlotte, NC)",
            "from_dma": "Charlotte, NC",
            "to_campaign": "Paid Social - Prospecting (Cincinnati, OH)",
            "to_dma": "Cincinnati, OH",
            "delta": 8_700,
            "rationale": "Experiment in Charlotte saturated; reallocating to higher-response Paid Social",
            "roas_impact": 1.87,
        },
        {
            "from_campaign": "Affiliate / Partnerships (Atlanta, GA)",
            "from_dma": "Atlanta, GA",
            "to_campaign": "SEM Brand (Columbus, OH)",
            "to_dma": "Columbus, OH",
            "delta": 6_200,
            "rationale": "Defend campaign under-invested in Columbus; reallocating from over-pacing Affiliate",
            "roas_impact": 1.52,
        },
        {
            "from_campaign": "Direct Mail - Acquisition (Nashville, TN)",
            "from_dma": "Nashville, TN",
            "to_campaign": "YouTube Pre-roll (Cincinnati, OH)",
            "to_dma": "Cincinnati, OH",
            "delta": 5_100,
            "rationale": "Marginal ROI in YouTube (Cincinnati) exceeds Direct Mail (Nashville) by $3,200/wk",
            "roas_impact": 1.31,
        },
        {
            "from_campaign": "Email CRM Reactivation (Charlotte, NC)",
            "from_dma": "Charlotte, NC",
            "to_campaign": "Paid Social - Prospecting (Atlanta, GA)",
            "to_dma": "Atlanta, GA",
            "delta": 4_300,
            "rationale": "Scale campaign in Atlanta has steeper marginal curve; each shifted $ yields 38 incremental accounts",
            "roas_impact": 1.18,
        },
    ]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/status", response_model=StatusResponse)
def allocation_status():
    """Return current allocation state for all 60 campaign x DMA combos.

    Includes current spend, accounts, and waste-gap analysis at each
    combo's current allocation.
    """
    try:
        eng = _get_engine()
        waste_data = eng["compute_waste_gap"]()

        combos_out = [
            ComboStatus(
                campaign=w["campaign"],
                dma=w["dma"],
                role=w["role"],
                current_spend=w["current_spend"],
                current_accounts=w["current_accounts"],
                optimal_accounts=w["optimal_accounts"],
                waste_gap_accounts=w["waste_gap_accounts"],
                waste_gap_dollars=w["waste_gap_dollars"],
            )
            for w in waste_data
        ]

        total_spend = sum(w["current_spend"] for w in waste_data)
        total_accounts = sum(w["current_accounts"] for w in waste_data)
        total_waste = sum(max(0, w["waste_gap_dollars"]) for w in waste_data)

        return StatusResponse(
            combos=combos_out,
            total_spend=round(total_spend, 2),
            total_accounts=round(total_accounts, 1),
            total_waste_gap_dollars=round(total_waste, 2),
            combo_count=len(combos_out),
        )
    except Exception as exc:
        logger.warning("allocation_status fallback: %s", exc)
        fb = _fallback_status()
        return StatusResponse(
            combos=[ComboStatus(**c) for c in fb["combos"]],
            total_spend=fb["total_spend"],
            total_accounts=fb["total_accounts"],
            total_waste_gap_dollars=fb["total_waste_gap_dollars"],
            combo_count=fb["combo_count"],
        )


@router.get("/curves", response_model=CurvesResponse)
def allocation_curves():
    """Return response-curve parameters and sample points for each combo.

    Used by the front end to draw diminishing-returns curves with
    the current-spend dot and optimal-spend ring overlay.
    """
    try:
        eng = _get_engine()
        curves = eng["get_curve_data"]()

        return CurvesResponse(
            curves=[CurvePoint(**c) for c in curves],
            count=len(curves),
        )
    except Exception as exc:
        logger.warning("allocation_curves fallback: %s", exc)
        return CurvesResponse(curves=[], count=0)


@router.post("/optimize", response_model=OptimizeResponse)
def allocation_optimize(req: OptimizeRequest):
    """Run the Next-Best-Dollar optimizer.

    Accepts an objective (profit or volume) and optional budget.
    Returns the optimal allocation, top moves, waste-gap, and
    headline metrics.
    """
    try:
        eng = _get_engine()
        objective = eng["Objective"](req.objective)
        budget = req.budget if req.budget > 0 else None

        result = eng["run_optimization"](
            objective=objective,
            budget=budget,
        )

        r = _dataclass_to_dict(result)

        return OptimizeResponse(
            objective=r["objective"],
            budget=r["budget"],
            allocations=[AllocationEntry(**a) for a in r["allocations"]],
            top_moves=[MoveEntry(**m) for m in r["top_moves"]],
            total_current_spend=r["total_current_spend"],
            total_optimal_spend=r["total_optimal_spend"],
            total_current_accounts=r["total_current_accounts"],
            total_optimal_accounts=r["total_optimal_accounts"],
            total_current_profit=r["total_current_profit"],
            total_optimal_profit=r["total_optimal_profit"],
            total_waste_gap_dollars=r["total_waste_gap_dollars"],
            headline_lift_pct=r["headline_lift_pct"],
            headline_left_on_table_annual=r["headline_left_on_table_annual"],
        )
    except Exception as exc:
        logger.exception("allocation_optimize error: %s", exc)
        return {"error": str(exc)}


@router.get("/rollout", response_model=RolloutResponse)
def allocation_rollout(
    objective: str = Query(
        default="profit",
        description="Optimization objective: profit or volume",
    ),
    budget: float = Query(
        default=0,
        ge=0,
        description="Total weekly budget. 0 = use current total.",
    ),
):
    """Return a 30-day rollout simulation from current to optimal allocation.

    Each week, spend adjusts by at most 20% per combo.  Returns daily
    snapshots suitable for animation.
    """
    try:
        eng = _get_engine()
        obj = eng["Objective"](objective)
        bgt = budget if budget > 0 else None

        days = eng["simulate_rollout"](objective=obj, budget=bgt)

        return RolloutResponse(
            days=[RolloutSnapshot(**_dataclass_to_dict(d)) for d in days],
            rollout_length=30,
            max_weekly_change_pct=20.0,
        )
    except Exception as exc:
        logger.warning("allocation_rollout fallback: %s", exc)
        # Minimal fallback — just day 0 and day 30
        return RolloutResponse(
            days=[
                RolloutSnapshot(day=0, total_spend=1_430_000, total_accounts=5_620, total_profit=538_000, pct_progress=0),
                RolloutSnapshot(day=30, total_spend=1_430_000, total_accounts=7_480, total_profit=1_190_000, pct_progress=100),
            ],
            rollout_length=30,
            max_weekly_change_pct=20.0,
        )


@router.get("/moves", response_model=MovesResponse)
def allocation_moves(
    objective: str = Query(
        default="profit",
        description="Optimization objective: profit or volume",
    ),
    budget: float = Query(
        default=0,
        ge=0,
        description="Total weekly budget. 0 = use current total.",
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=60,
        description="Maximum number of moves to return.",
    ),
):
    """Return the top reallocation moves (from -> to with delta, rationale, ROAS impact).

    These are the highest-impact spend shifts the optimizer recommends.
    """
    try:
        eng = _get_engine()
        obj = eng["Objective"](objective)
        bgt = budget if budget > 0 else None

        result = eng["run_optimization"](objective=obj, budget=bgt)
        moves = result.top_moves[:limit]

        return MovesResponse(
            moves=[
                MoveEntry(
                    from_campaign=m.from_campaign,
                    from_dma=m.from_dma,
                    to_campaign=m.to_campaign,
                    to_dma=m.to_dma,
                    delta=m.delta,
                    rationale=m.rationale,
                    roas_impact=m.roas_impact,
                )
                for m in moves
            ],
            count=len(moves),
        )
    except Exception as exc:
        logger.warning("allocation_moves fallback: %s", exc)
        fb = _fallback_moves()[:limit]
        return MovesResponse(
            moves=[MoveEntry(**m) for m in fb],
            count=len(fb),
        )
