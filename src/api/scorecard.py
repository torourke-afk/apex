"""Scorecard API endpoints.

GET /api/scorecard/kpis              — KPI summary with sparklines and trend
GET /api/scorecard/financial-summary — MTD/QTD/YTD spend, CPL, ROAS
GET /api/scorecard/alerts            — Recent alerts, filterable by severity
"""

from datetime import datetime, date, timedelta
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.data.scorecard_queries import (
    get_kpi_summary,
    get_financial_summary,
    get_campaign_performance,
    get_recent_alerts,
)


def _call_cached(fn, *args, **kwargs):
    """Call a data-layer function, bypassing Streamlit cache decorator.

    Outside Streamlit, @st.cache_data uses MemoryCacheStorageManager which
    does NOT honour TTL — results are cached forever.  We always unwrap to
    the underlying function so the BFF gets fresh DB reads on every request.
    """
    underlying = getattr(fn, "__wrapped__", None)
    if underlying is not None:
        return underlying(*args, **kwargs)
    return fn(*args, **kwargs)


def _default_filters(
    date_start: str | None = None,
    date_end: str | None = None,
    dma: str | None = None,
) -> dict:
    """Build a filter dict with sensible date defaults (YTD to today)."""
    today = date.today()
    filters: dict = {}
    filters["date_end"] = date_end or str(today)
    filters["date_start"] = date_start or str(today.replace(month=1, day=1))
    if dma:
        from src.api.spend import _resolve_dma_codes
        raw = [d.strip() for d in dma.split(",")]
        filters["dma"] = _resolve_dma_codes(raw)
    return filters

router = APIRouter(prefix="/api/scorecard", tags=["scorecard"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class KPIItem(BaseModel):
    name: str
    value: float
    target: float
    delta: float
    delta_pct: float
    sparkline_data: list[float]
    trend: Literal["improving", "declining", "flat"]
    alert_status: str | None
    format_type: str | None = None


class KPISummaryResponse(BaseModel):
    kpis: list[KPIItem]
    as_of: datetime


class FinancialMetric(BaseModel):
    label: str
    value: float
    delta: float
    format: str


class FinancialSummaryResponse(BaseModel):
    metrics: list[FinancialMetric]
    as_of: datetime


class AlertItem(BaseModel):
    severity: Literal["error", "warning", "info"]
    kpi_name: str
    description: str
    created_at: str
    module_link: str | None = None


class AlertsResponse(BaseModel):
    alerts: list[AlertItem]
    total_count: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/kpis", response_model=KPISummaryResponse)
def kpis(
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    product: str | None = Query(default=None, description="Comma-separated product filter"),
    dma: str | None = Query(default=None, description="Comma-separated DMA filter"),
    channel: str | None = Query(default=None, description="Comma-separated channel filter"),
):
    """Return KPI summary with sparklines and trend direction."""
    filters = _default_filters(date_start, date_end, dma)
    data = _call_cached(get_kpi_summary, filters)
    kpi_items = [
        KPIItem(
            name=k["name"],
            value=float(k.get("value", 0)),
            target=float(k.get("target", 0)),
            delta=float(k.get("delta", 0)),
            delta_pct=float(k.get("delta_pct", 0)),
            sparkline_data=[float(x) for x in k.get("sparkline_data", [])],
            trend=k.get("trend", "flat"),
            alert_status=k.get("alert_status"),
            format_type=k.get("format_type"),
        )
        for k in data
    ]
    return KPISummaryResponse(kpis=kpi_items, as_of=datetime.now())


@router.get("/financial-summary", response_model=FinancialSummaryResponse)
def financial_summary(
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    product: str | None = Query(default=None, description="Comma-separated product filter"),
    dma: str | None = Query(default=None, description="Comma-separated DMA filter"),
    channel: str | None = Query(default=None, description="Comma-separated channel filter"),
):
    """Return MTD/QTD/YTD financial metrics."""
    filters = _default_filters(date_start, date_end, dma)
    data = _call_cached(get_financial_summary, filters)
    metrics = [
        FinancialMetric(
            label=m["label"],
            value=float(m.get("value", 0)),
            delta=float(m.get("delta", 0)),
            format=m.get("format", "number"),
        )
        for m in data
    ]
    return FinancialSummaryResponse(metrics=metrics, as_of=datetime.now())


class CampaignItem(BaseModel):
    name: str
    channel: str
    spend: float
    roas: float
    funded: int
    badge: str  # "green" | "amber" | "red"


class CampaignResponse(BaseModel):
    campaigns: list[CampaignItem]
    count: int


@router.get("/campaigns", response_model=CampaignResponse)
def campaigns(
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    product: str | None = Query(default=None, description="Comma-separated product filter"),
    dma: str | None = Query(default=None, description="Comma-separated DMA filter"),
    channel: str | None = Query(default=None, description="Comma-separated channel filter"),
):
    """Return top campaign performance data."""
    filters = _default_filters(date_start, date_end, dma)
    data = _call_cached(get_campaign_performance, filters)
    items = []
    for c in data:
        spend = float(c.get("Spend", 0))
        roas = float(c.get("ROAS", 0))
        funded = int(c.get("Funded", 0))
        badge = "green" if roas >= 3.5 else "amber" if roas >= 2.5 else "red"
        # Derive a short channel label from campaign name
        name = c.get("Campaign", "Unknown")
        ch = "SEM"
        for prefix, label in [("Display", "Display"), ("Social", "Social"), ("DM", "DM"),
                              ("Direct Mail", "DM"), ("Brand", "TV"), ("Affiliate", "Affiliate"),
                              ("Email", "Email")]:
            if prefix.lower() in name.lower():
                ch = label
                break
        items.append(CampaignItem(
            name=name,
            channel=ch,
            spend=spend,
            roas=roas,
            funded=funded,
            badge=badge,
        ))
    # Sort by ROAS descending, take top 6
    items.sort(key=lambda x: x.roas, reverse=True)
    items = items[:6]
    return CampaignResponse(campaigns=items, count=len(items))


@router.get("/alerts", response_model=AlertsResponse)
def alerts(
    severity: str | None = Query(default=None, description="Filter by severity: error, warning, info"),
    limit: int = Query(default=10, ge=1, le=200, description="Max alerts to return"),
):
    """Return recent alerts, optionally filtered by severity."""
    data = _call_cached(get_recent_alerts, severity=severity, limit=limit)
    alert_items = [
        AlertItem(
            severity=a["severity"],
            kpi_name=a.get("kpi", a.get("kpi_name", "")),
            description=a.get("desc", a.get("description", "")),
            created_at=a.get("ts", a.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M"))),
            module_link=a.get("module_link"),
        )
        for a in data
    ]
    return AlertsResponse(alerts=alert_items, total_count=len(alert_items))
