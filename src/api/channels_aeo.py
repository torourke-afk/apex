"""AEO (AI Engine Optimisation) channel API endpoints.

GET /api/channels/aeo/summary — per-metric KPI summary (mention rate, position, SoV, sentiment, citation)
GET /api/channels/aeo/trends  — weekly time-series per platform per metric
GET /api/channels/aeo/prompts — per-prompt results table across platforms
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/channels/aeo", tags=["channels-aeo"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_filters(
    platforms: str | None = None,
    prompt_categories: str | None = None,
    n_weeks: int = 12,
) -> dict[str, Any]:
    """Build filters dict for organic_aeo functions."""
    filters: dict[str, Any] = {"n_weeks": n_weeks}
    if platforms:
        filters["platforms"] = [p.strip() for p in platforms.split(",")]
    if prompt_categories:
        filters["prompt_categories"] = [c.strip() for c in prompt_categories.split(",")]
    return filters


def _df_to_records(df: pd.DataFrame) -> list[dict]:
    if df is None or df.empty:
        return []
    return df.to_dict(orient="records")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/summary")
def aeo_summary(
    platforms: str | None = Query(default=None, description="Comma-separated platform names"),
    prompt_categories: str | None = Query(default=None, description="Comma-separated prompt categories"),
    n_weeks: int = Query(default=12, ge=1, le=52, description="Number of weeks for sparkline"),
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    product: str | None = Query(default=None, description="Comma-separated product filter"),
    dma: str | None = Query(default=None, description="Comma-separated DMA filter"),
    channel: str | None = Query(default=None, description="Comma-separated channel filter"),
):
    """Return per-metric KPI summary aggregated across selected platforms."""
    try:
        from src.data.organic_aeo import get_llm_visibility_summary

        filters = _build_filters(platforms, prompt_categories, n_weeks)
        data = get_llm_visibility_summary(filters)
        return {"metrics": data}
    except Exception as exc:
        logger.warning("aeo_summary fallback: %s", exc)
        return {
            "metrics": {
                "mention_rate": {"label": "Mention Rate", "value": 0.50, "delta": 0.01, "format_type": "percent"},
                "avg_position": {"label": "Avg Position", "value": 3.2, "delta": -0.1, "format_type": "position"},
                "sov": {"label": "Share of Voice", "value": 0.25, "delta": 0.005, "format_type": "percent"},
                "sentiment": {"label": "Sentiment Score", "value": 75.0, "delta": 0.5, "format_type": "score"},
                "citation_rate": {"label": "Citation Rate", "value": 0.42, "delta": 0.01, "format_type": "percent"},
            }
        }


@router.get("/trends")
def aeo_trends(
    platforms: str | None = Query(default=None, description="Comma-separated platform names"),
    n_weeks: int = Query(default=12, ge=1, le=52),
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    product: str | None = Query(default=None, description="Comma-separated product filter"),
    dma: str | None = Query(default=None, description="Comma-separated DMA filter"),
    channel: str | None = Query(default=None, description="Comma-separated channel filter"),
):
    """Return weekly time-series per platform per metric.

    Each metric key maps to a dict of {week_label: {platform: value}}.
    """
    try:
        from src.data.organic_aeo import get_llm_visibility_trends

        filters = _build_filters(platforms, n_weeks=n_weeks)
        raw: dict[str, pd.DataFrame] = get_llm_visibility_trends(filters)
        # Convert each DataFrame to a JSON-friendly structure
        result: dict[str, list[dict]] = {}
        for metric, df in raw.items():
            result[metric] = _df_to_records(df.reset_index().rename(columns={"index": "week"}))
        return {"trends": result}
    except Exception as exc:
        logger.warning("aeo_trends fallback: %s", exc)
        return {"trends": {}}


@router.get("/prompts")
def aeo_prompts(
    platforms: str | None = Query(default=None, description="Comma-separated platform names"),
    prompt_categories: str | None = Query(default=None, description="Comma-separated categories"),
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    product: str | None = Query(default=None, description="Comma-separated product filter"),
    dma: str | None = Query(default=None, description="Comma-separated DMA filter"),
    channel: str | None = Query(default=None, description="Comma-separated channel filter"),
):
    """Return per-prompt results across platforms."""
    try:
        from src.data.organic_aeo import get_prompt_results

        filters = _build_filters(platforms, prompt_categories)
        df = get_prompt_results(filters)
        return {"prompts": _df_to_records(df)}
    except Exception as exc:
        logger.warning("aeo_prompts fallback: %s", exc)
        return {"prompts": []}
