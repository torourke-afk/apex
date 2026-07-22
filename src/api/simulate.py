"""Simulator API endpoints.

POST /api/simulate/     — run a simulation with custom scenario configuration
GET  /api/simulate/presets — list available scenario presets
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/simulate", tags=["simulator"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ChannelConfigInput(BaseModel):
    spend_pct: float = Field(ge=0, le=1, description="Fraction of total budget (0-1)")
    cpc: float = Field(ge=0, description="Cost per click")
    cpl: float = Field(ge=0, description="Cost per lead")
    use_cpl: bool = Field(default=False, description="Use CPL model instead of CPC")
    brand_lift_pct: float = Field(default=0.0, ge=0, description="Brand lift fraction")


class ScenarioRequest(BaseModel):
    name: str = Field(default="Custom Scenario")
    mode: str = Field(default="bd", description="bd or client")
    total_spend: float = Field(default=500_000.0, gt=0)
    channels: dict[str, ChannelConfigInput] = Field(default_factory=dict)
    organic_multiplier: float = Field(default=0.12, ge=0)
    aeo_rate: float = Field(default=0.04, ge=0)
    visit_to_app_start: float = Field(default=0.06, ge=0, le=1)
    app_start_to_apply: float = Field(default=0.68, ge=0, le=1)
    apply_to_approve: float = Field(default=0.52, ge=0, le=1)
    approve_to_open: float = Field(default=0.91, ge=0, le=1)
    open_to_fund: float = Field(default=0.72, ge=0, le=1)
    mob6_rate: float = Field(default=0.78, ge=0, le=1)
    mob12_rate: float = Field(default=0.65, ge=0, le=1)
    pfi_conversion_rate: float = Field(default=0.22, ge=0, le=1)
    ltv_per_hh: float = Field(default=950.0, ge=0)
    pfi_ltv_multiplier: float = Field(default=2.9, ge=0)
    run_comparison: bool = Field(
        default=False,
        description="If True, also run RVGT-improved scenario and return delta",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dataclass_to_dict(obj) -> dict[str, Any]:
    """Recursively convert a dataclass to a JSON-serializable dict."""
    result = asdict(obj)
    # Handle inf/nan values
    _sanitize_dict(result)
    return result


def _sanitize_dict(d: dict) -> None:
    """Replace inf/nan float values with None for JSON safety."""
    import math

    for key, val in d.items():
        if isinstance(val, float) and (math.isinf(val) or math.isnan(val)):
            d[key] = None
        elif isinstance(val, dict):
            _sanitize_dict(val)


def _request_to_scenario(req: ScenarioRequest):
    """Convert a ScenarioRequest Pydantic model to a ScenarioInput dataclass."""
    from src.simulator.engine import ScenarioInput, ChannelConfig, SimulatorMode

    channels = {}
    for ch_name, ch_cfg in req.channels.items():
        channels[ch_name] = ChannelConfig(
            spend_pct=ch_cfg.spend_pct,
            cpc=ch_cfg.cpc,
            cpl=ch_cfg.cpl,
            use_cpl=ch_cfg.use_cpl,
            brand_lift_pct=ch_cfg.brand_lift_pct,
        )

    mode = SimulatorMode.BD if req.mode.lower() == "bd" else SimulatorMode.CLIENT

    return ScenarioInput(
        name=req.name,
        mode=mode,
        total_spend=req.total_spend,
        channels=channels,
        organic_multiplier=req.organic_multiplier,
        aeo_rate=req.aeo_rate,
        visit_to_app_start=req.visit_to_app_start,
        app_start_to_apply=req.app_start_to_apply,
        apply_to_approve=req.apply_to_approve,
        approve_to_open=req.approve_to_open,
        open_to_fund=req.open_to_fund,
        mob6_rate=req.mob6_rate,
        mob12_rate=req.mob12_rate,
        pfi_conversion_rate=req.pfi_conversion_rate,
        ltv_per_hh=req.ltv_per_hh,
        pfi_ltv_multiplier=req.pfi_ltv_multiplier,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/")
def run_simulate(req: ScenarioRequest):
    """Run the 5-stage waterfall simulation.

    Optionally returns a before/after comparison when run_comparison=True.
    """
    try:
        from src.simulator.engine import run_simulation, run_comparison

        scenario = _request_to_scenario(req)

        if req.run_comparison:
            comparison = run_comparison(scenario)
            return {
                "before": _dataclass_to_dict(comparison.before),
                "after": _dataclass_to_dict(comparison.after),
                "delta": comparison.delta,
                "pct_change": comparison.pct_change,
            }
        else:
            result = run_simulation(scenario)
            return _dataclass_to_dict(result)
    except Exception as exc:
        logger.exception("simulate error: %s", exc)
        return {"error": str(exc)}


@router.get("/presets")
def simulate_presets():
    """Return available simulation preset names with descriptions + slider configs."""
    presets = [
        {
            "name": "regional_growth",
            "label": "Regional Growth",
            "description": "Mid-size regional bank ($15-25B assets), organic growth strategy",
        },
        {
            "name": "top_20",
            "label": "Top 20",
            "description": "Large national bank ($100B+ assets), efficiency-focused",
        },
        {
            "name": "community",
            "label": "Community Bank",
            "description": "Small community bank (<$2B assets), relationship-driven",
        },
        {
            "name": "de_novo",
            "label": "De Novo",
            "description": "New digital-first bank, high CAC / fast funnel",
        },
        {
            "name": "acquisition_integration",
            "label": "Acquisition Integration",
            "description": "Post-acquisition bank, retention-focused",
        },
    ]

    try:
        from src.simulator.engine import load_preset

        for p in presets:
            try:
                cfg = load_preset(p["name"])
                budget_m = cfg.total_spend / 1_000_000
                # Map engine channels to UI sliders (brand = non-SEM/social/email)
                sem_pct = round((cfg.channels.get("sem", type("", (), {"spend_pct": 0})).spend_pct) * 100)
                social_pct = round((cfg.channels.get("social", type("", (), {"spend_pct": 0})).spend_pct) * 100)
                # Everything else is "brand" in the UI
                brand_pct = max(0, 100 - sem_pct - social_pct)
                p["available"] = True
                p["config"] = {
                    "budget": round(budget_m, 1),
                    "brand": brand_pct,
                    "sem": sem_pct,
                    "social": social_pct,
                }
            except Exception:
                p["available"] = False
                p["config"] = None
    except Exception:
        for p in presets:
            p["available"] = False
            p["config"] = None

    return {"presets": presets}
