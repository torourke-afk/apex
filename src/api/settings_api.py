"""Settings API endpoints.

GET /api/settings/benchmarks — current benchmark configuration
GET /api/settings/mode       — current application mode (BD / Client)
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/benchmarks")
def settings_benchmarks(
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    product: str | None = Query(default=None, description="Comma-separated product filter"),
    dma: str | None = Query(default=None, description="Comma-separated DMA filter"),
    channel: str | None = Query(default=None, description="Comma-separated channel filter"),
):
    """Return current benchmark configuration values.

    Merges SEM benchmarks, social benchmarks, and simulator benchmarks
    into a single response for the settings panel.
    """
    benchmarks: dict = {
        "sem": {
            "cpc": 3.46,
            "ctr": 0.083,
            "cvr": 0.0255,
            "cpl": 83.93,
            "quality_score": 7.0,
            "impression_share_branded": 0.90,
        },
        "social": {
            "cpl_sem": 48.50,
            "native_cvr": 13.0,
            "lp_cvr": 4.02,
            "ai_cpa_vs_manual": -10.0,
            "fp_audiences": 15,
        },
    }

    # Try to load simulator benchmarks from the JSON file
    try:
        from src.simulator.engine import _load_benchmarks

        sim_bm = _load_benchmarks()
        benchmarks["simulator"] = {
            "channels": sim_bm.get("channels", {}),
            "organic": sim_bm.get("organic", {}),
            "ltv": sim_bm.get("ltv", {}),
        }
    except Exception as exc:
        logger.debug("Could not load simulator benchmarks: %s", exc)
        benchmarks["simulator"] = {}

    return {"benchmarks": benchmarks}


@router.get("/mode")
def settings_mode():
    """Return current application mode and key configuration.

    Mode is determined by the APEX_MODE environment variable:
    - 'bd' (default) — Business Development: pitching prospects
    - 'client' — Active client engagement tracking
    """
    mode = os.environ.get("APEX_MODE", "bd").lower()
    if mode not in ("bd", "client"):
        mode = "bd"

    return {
        "mode": mode,
        "mode_label": "Business Development" if mode == "bd" else "Client",
        "debug": os.environ.get("APEX_DEBUG_MODE", "").strip() in ("1", "true", "yes"),
        "db_path": os.environ.get("APEX_DB_PATH", "apex_clean.duckdb"),
        "app_version": "0.1.0",
    }
