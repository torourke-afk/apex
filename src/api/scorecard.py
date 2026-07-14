"""Scorecard API endpoints.

GET /api/scorecard/kpis              — KPI summary with sparklines and trend
GET /api/scorecard/financial-summary — MTD/QTD/YTD spend, CPL, ROAS
GET /api/scorecard/alerts            — Recent alerts, filterable by severity
"""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.data.scorecard_queries import (
    get_kpi_summary,
    get_financial_summary,
    get_recent_alerts,
)

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
def kpis():
    """Return KPI summary with sparklines and trend direction."""
    data = get_kpi_summary()
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
def financial_summary():
    """Return MTD/QTD/YTD financial metrics."""
    data = get_financial_summary()
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


@router.get("/alerts", response_model=AlertsResponse)
def alerts(
    severity: str | None = Query(default=None, description="Filter by severity: error, warning, info"),
    limit: int = Query(default=10, ge=1, le=200, description="Max alerts to return"),
):
    """Return recent alerts, optionally filtered by severity."""
    data = get_recent_alerts(severity=severity, limit=limit)
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
