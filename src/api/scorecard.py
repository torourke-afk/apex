"""Scorecard API endpoints.

GET /api/scorecard/kpis              — KPI summary with sparklines and trend
GET /api/scorecard/financial-summary — MTD/QTD/YTD spend, CPL, ROAS
GET /api/scorecard/alerts            — Recent alerts, filterable by severity
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.data.database import get_session
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


class KPISummaryResponse(BaseModel):
    kpis: list[KPIItem]
    as_of: datetime


class FinancialSummaryResponse(BaseModel):
    media_spend_mtd: Decimal
    media_spend_qtd: Decimal
    media_spend_ytd: Decimal
    spend_vs_plan_mtd: Decimal
    spend_vs_plan_qtd: Decimal
    spend_vs_plan_ytd: Decimal
    blended_cpl: Decimal
    blended_cpihh: Decimal
    cpl_trend: Literal["improving", "declining", "flat"]
    cpihh_trend: Literal["improving", "declining", "flat"]
    revenue_attribution: Decimal
    brand_burn_rate: float
    incremental_spend_vs_budget: Decimal


class AlertItem(BaseModel):
    severity: Literal["error", "warning", "info"]
    kpi_name: str
    description: str
    created_at: datetime
    module_link: str | None


class AlertsResponse(BaseModel):
    alerts: list[AlertItem]
    total_count: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/kpis", response_model=KPISummaryResponse)
def kpis(db: Session = Depends(get_session)):
    """Return KPI summary with sparklines and trend direction."""
    data = get_kpi_summary(db)
    return KPISummaryResponse(**data)


@router.get("/financial-summary", response_model=FinancialSummaryResponse)
def financial_summary(db: Session = Depends(get_session)):
    """Return MTD/QTD/YTD financial metrics."""
    data = get_financial_summary(db)
    return FinancialSummaryResponse(**data)


@router.get("/alerts", response_model=AlertsResponse)
def alerts(
    severity: str | None = Query(default=None, description="Filter by severity: error, warning, info"),
    limit: int = Query(default=10, ge=1, le=200, description="Max alerts to return"),
    db: Session = Depends(get_session),
):
    """Return recent alerts, optionally filtered by severity."""
    data = get_recent_alerts(db, severity=severity, limit=limit)
    return AlertsResponse(**data)
