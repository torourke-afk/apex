"""SEM channel API endpoints.

GET /api/channels/sem/overview    — headline SEM metrics with alert badges
GET /api/channels/sem/keywords    — keyword group table (paginated + sortable)
GET /api/channels/sem/trends      — time-series for any SEM metric
GET /api/channels/sem/match-types — match type allocation and per-type performance

Depends on src.data.sem_queries (delivered by APE-89).

Benchmark constants match the APE-16 spec:
  CPC       $3.46   alert if non-branded > $5.00
  CTR       8.3 %   alert if < 6 %
  CVR       2.55 %  alert if < 2.0 %
  CPL      $83.93   alert if > $100
  QS        7+      alert if avg < 5
  IS brand  90 %+   alert if branded < 85 %
  VBB       positive trend — signal degradation triggers alert
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.data.database import get_session
from src.data.sem_queries import (
    get_sem_overview,
    get_sem_keywords,
    get_sem_trends,
    get_sem_match_types,
)

router = APIRouter(prefix="/api/channels/sem", tags=["sem"])


# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------

BENCHMARKS = {
    "cpc": 3.46,
    "ctr": 0.083,
    "cvr": 0.0255,
    "cpl": 83.93,
    "quality_score": 7.0,
    "impression_share_branded": 0.90,
}

_ALERT_THRESHOLDS: dict[str, tuple[str, float]] = {
    # (direction, threshold): "above" means alert when value > threshold
    "cpc_non_branded": ("above", 5.00),
    "ctr": ("below", 0.06),
    "cvr": ("below", 0.02),
    "cpl": ("above", 100.00),
    "quality_score": ("below", 5.0),
    "impression_share_branded": ("below", 0.85),
}


def _alert_status(metric: str, value: float) -> str | None:
    if metric not in _ALERT_THRESHOLDS:
        return None
    direction, threshold = _ALERT_THRESHOLDS[metric]
    if direction == "above" and value > threshold:
        return "error"
    if direction == "below" and value < threshold:
        return "error"
    return None


# ---------------------------------------------------------------------------
# Response models — Overview
# ---------------------------------------------------------------------------

class SEMMetricItem(BaseModel):
    name: str
    value: float
    benchmark: float | None
    alert_status: str | None


class SEMOverviewResponse(BaseModel):
    avg_cpc: float
    avg_ctr: float
    avg_cvr: float
    avg_cpl: float
    avg_quality_score: float
    impression_share_branded: float
    vbb_margin_signal: float
    negative_keyword_score: float
    metrics: list[SEMMetricItem]
    alerts: list[str]


# ---------------------------------------------------------------------------
# Response models — Keywords
# ---------------------------------------------------------------------------

class KeywordGroupItem(BaseModel):
    keyword_group: str
    match_type: Literal["broad", "exact", "phrase"]
    intent_type: Literal["branded", "non_branded", "pmax"]
    market_segment: Literal["established", "growth", "new"]
    quality_score: int
    spend: float
    clicks: int
    impressions: int
    conversions: int
    cpc: float
    ctr: float
    cvr: float
    cpl: float
    impression_share: float
    is_active: bool


class KeywordGroupsResponse(BaseModel):
    groups: list[KeywordGroupItem]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Response models — Trends
# ---------------------------------------------------------------------------

class TrendPoint(BaseModel):
    date: str
    value: float


class SEMTrendsResponse(BaseModel):
    metric: str
    period: str
    data: list[TrendPoint]
    benchmark: float | None


# ---------------------------------------------------------------------------
# Response models — Match Types
# ---------------------------------------------------------------------------

class MatchTypeItem(BaseModel):
    match_type: Literal["broad", "exact", "phrase"]
    spend: float
    spend_pct: float
    clicks: int
    impressions: int
    conversions: int
    cpc: float
    ctr: float
    cvr: float
    cpl: float


class MatchTypesResponse(BaseModel):
    match_types: list[MatchTypeItem]
    total_spend: float


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/overview", response_model=SEMOverviewResponse)
def sem_overview(
    start_date: str | None = Query(default=None, description="ISO date filter start (YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="ISO date filter end (YYYY-MM-DD)"),
    db: Session = Depends(get_session),
):
    """Return headline SEM metrics with alert badges and benchmark context."""
    data = get_sem_overview(db, start_date=start_date, end_date=end_date)

    avg_cpc = data.get("avg_cpc", 0.0)
    avg_ctr = data.get("avg_ctr", 0.0)
    avg_cvr = data.get("avg_cvr", 0.0)
    avg_cpl = data.get("avg_cpl", 0.0)
    avg_qs = data.get("avg_quality_score", 0.0)
    is_branded = data.get("impression_share_branded", 0.0)
    vbb = data.get("vbb_margin_signal", 0.0)
    neg_kw_score = data.get("negative_keyword_score", 0.0)

    alerts: list[str] = []
    if avg_cpc > 5.00:
        alerts.append(f"Non-branded CPC ${avg_cpc:.2f} exceeds $5.00 threshold")
    if avg_ctr < 0.06:
        alerts.append(f"CTR {avg_ctr*100:.1f}% below 6% threshold")
    if avg_cvr < 0.02:
        alerts.append(f"CVR {avg_cvr*100:.2f}% below 2% threshold")
    if avg_cpl > 100.00:
        alerts.append(f"CPL ${avg_cpl:.2f} exceeds $100 threshold")
    if avg_qs < 5.0:
        alerts.append(f"Avg Quality Score {avg_qs:.1f} below threshold of 5")
    if is_branded < 0.85:
        alerts.append(f"Branded impression share {is_branded*100:.1f}% below 85%")

    metrics = [
        SEMMetricItem(
            name="Avg CPC",
            value=avg_cpc,
            benchmark=BENCHMARKS["cpc"],
            alert_status=_alert_status("cpc_non_branded", avg_cpc),
        ),
        SEMMetricItem(
            name="CTR",
            value=avg_ctr,
            benchmark=BENCHMARKS["ctr"],
            alert_status=_alert_status("ctr", avg_ctr),
        ),
        SEMMetricItem(
            name="CVR",
            value=avg_cvr,
            benchmark=BENCHMARKS["cvr"],
            alert_status=_alert_status("cvr", avg_cvr),
        ),
        SEMMetricItem(
            name="CPL",
            value=avg_cpl,
            benchmark=BENCHMARKS["cpl"],
            alert_status=_alert_status("cpl", avg_cpl),
        ),
        SEMMetricItem(
            name="Quality Score",
            value=avg_qs,
            benchmark=BENCHMARKS["quality_score"],
            alert_status=_alert_status("quality_score", avg_qs),
        ),
        SEMMetricItem(
            name="Impression Share (Branded)",
            value=is_branded,
            benchmark=BENCHMARKS["impression_share_branded"],
            alert_status=_alert_status("impression_share_branded", is_branded),
        ),
        SEMMetricItem(
            name="VBB Margin Signal",
            value=vbb,
            benchmark=None,
            alert_status="error" if vbb < 0 else None,
        ),
    ]

    return SEMOverviewResponse(
        avg_cpc=avg_cpc,
        avg_ctr=avg_ctr,
        avg_cvr=avg_cvr,
        avg_cpl=avg_cpl,
        avg_quality_score=avg_qs,
        impression_share_branded=is_branded,
        vbb_margin_signal=vbb,
        negative_keyword_score=neg_kw_score,
        metrics=metrics,
        alerts=alerts,
    )


@router.get("/keywords", response_model=KeywordGroupsResponse)
def sem_keywords(
    sort: Literal["spend", "conversions", "cpa", "cpc", "ctr", "cvr", "quality_score"] = Query(
        default="spend", description="Column to sort by (descending)"
    ),
    intent_type: str | None = Query(default=None, description="Filter: branded|non_branded|pmax"),
    match_type: str | None = Query(default=None, description="Filter: broad|exact|phrase"),
    market_segment: str | None = Query(default=None, description="Filter: established|growth|new"),
    is_active: bool | None = Query(default=None, description="Filter by active status"),
    start_date: str | None = Query(default=None, description="ISO date filter start"),
    end_date: str | None = Query(default=None, description="ISO date filter end"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=500, description="Rows per page"),
    db: Session = Depends(get_session),
):
    """Return keyword group performance table, sorted and paginated."""
    filters = {}
    if intent_type:
        filters["intent_type"] = intent_type
    if match_type:
        filters["match_type"] = match_type
    if market_segment:
        filters["market_segment"] = market_segment
    if is_active is not None:
        filters["is_active"] = is_active

    data = get_sem_keywords(
        db,
        sort=sort,
        filters=filters,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

    return KeywordGroupsResponse(
        groups=[KeywordGroupItem(**g) for g in data["groups"]],
        total=data["total"],
        page=page,
        page_size=page_size,
    )


@router.get("/trends", response_model=SEMTrendsResponse)
def sem_trends(
    metric: Literal["cpc", "ctr", "cvr", "cpl", "quality_score", "impression_share", "vbb_margin_signal", "spend"] = Query(
        default="cpc", description="Metric to plot over time"
    ),
    period: Literal["7d", "30d", "60d", "90d"] = Query(
        default="30d", description="Look-back window"
    ),
    intent_type: str | None = Query(default=None, description="Filter by intent type"),
    market_segment: str | None = Query(default=None, description="Filter by market segment"),
    db: Session = Depends(get_session),
):
    """Return daily time-series for a single SEM metric."""
    data = get_sem_trends(
        db,
        metric=metric,
        period=period,
        intent_type=intent_type,
        market_segment=market_segment,
    )

    return SEMTrendsResponse(
        metric=metric,
        period=period,
        data=[TrendPoint(**pt) for pt in data["points"]],
        benchmark=BENCHMARKS.get(metric),
    )


@router.get("/match-types", response_model=MatchTypesResponse)
def sem_match_types(
    start_date: str | None = Query(default=None, description="ISO date filter start"),
    end_date: str | None = Query(default=None, description="ISO date filter end"),
    db: Session = Depends(get_session),
):
    """Return match type allocation and per-type performance metrics."""
    data = get_sem_match_types(db, start_date=start_date, end_date=end_date)

    total_spend = sum(mt["spend"] for mt in data["match_types"])
    match_types = [
        MatchTypeItem(
            spend_pct=(mt["spend"] / total_spend * 100) if total_spend > 0 else 0.0,
            **mt,
        )
        for mt in data["match_types"]
    ]

    return MatchTypesResponse(
        match_types=match_types,
        total_spend=total_spend,
    )
