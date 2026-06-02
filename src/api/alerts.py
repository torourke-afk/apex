"""Alerts REST API.

GET  /api/alerts                    — List alerts, filterable by severity/since
POST /api/alerts/evaluate           — Trigger a manual evaluation cycle
PATCH /api/alerts/{alert_id}/acknowledge — Mark an alert as acknowledged
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.data.alert_engine import DEFAULT_ALERT_RULES, evaluate_alerts
from src.data.database import get_session
from src.data.orm import Alert as AlertORM

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class AlertResponse(BaseModel):
    id: uuid.UUID
    title: str
    severity: str
    category: str
    message: str
    acknowledged: bool
    resolved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_row(cls, row: AlertORM) -> "AlertResponse":
        return cls(
            id=row.id,
            title=row.title,
            severity=row.severity,
            category=row.category,
            message=row.message,
            acknowledged=row.is_read,
            resolved_at=row.resolved_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class EvaluateResponse(BaseModel):
    evaluated: bool
    alerts_fired: int


# ---------------------------------------------------------------------------
# KPI metric data for evaluation
# ---------------------------------------------------------------------------

# Seed sparklines keyed by alert-rule KPI name.
# Each list is oldest → newest; last value = current.
_KPI_SPARKLINES: dict[str, list[float]] = {
    "Net HH Growth":            [11200, 11400, 11500, 11650, 11800, 11900, 12000, 12050, 12100, 12200, 12350, 12450],
    "MOB6 Retention":           [81.0, 81.5, 82.1, 82.8, 83.0, 83.4, 83.8, 84.0, 84.1, 84.2, 84.3, 84.3],
    "Brand Capture Rate":       [40.1, 39.8, 39.5, 39.2, 39.0, 38.9, 38.8, 38.7, 38.7, 38.7, 38.7, 38.7],
    "CPIHH":                    [345, 338, 332, 328, 324, 322, 320, 318, 316, 314, 313, 312],
    "LLM Visibility":           [51.0, 53.0, 55.5, 57.0, 58.0, 59.2, 60.0, 60.8, 61.5, 62.0, 62.2, 62.4],
    "App Completion Rate":      [74.5, 74.2, 73.8, 73.5, 73.0, 72.6, 72.3, 72.1, 72.0, 71.9, 71.8, 71.8],
    # SEM metrics: placeholder values (not in scorecard seed)
    "SEM CPC (non-branded)":    [4.20, 4.25, 4.30, 4.35, 4.40, 4.50, 4.60, 4.70, 4.80, 4.90, 5.05, 5.10],
    "SEM Quality Score":        [7.2, 7.1, 6.9, 6.8, 6.7, 6.5, 6.4, 6.2, 6.0, 5.8, 5.5, 5.2],
    "Impression Share (branded)": [90, 89, 88, 88, 87, 87, 86, 86, 85, 84, 83, 82],
}


def _build_metrics() -> tuple[dict[str, float], list[dict[str, float]]]:
    """Build current_metrics and historical_metrics from seed sparklines."""
    current_metrics: dict[str, float] = {}
    # historical_metrics is a list of period dicts, oldest first, not including current
    max_len = max(len(v) for v in _KPI_SPARKLINES.values())
    historical: list[dict[str, float]] = [{} for _ in range(max_len - 1)]

    for kpi_name, sparkline in _KPI_SPARKLINES.items():
        current_metrics[kpi_name] = sparkline[-1]
        for i, val in enumerate(sparkline[:-1]):
            historical[i][kpi_name] = val

    return current_metrics, historical


# ---------------------------------------------------------------------------
# Shared evaluation logic (used by endpoint and scheduler)
# ---------------------------------------------------------------------------

def run_evaluation() -> int:
    """Run alert evaluation and return count of newly fired alerts."""
    current_metrics, historical_metrics = _build_metrics()
    fired = evaluate_alerts(current_metrics, historical_metrics, DEFAULT_ALERT_RULES)
    return len(fired)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[AlertResponse])
def list_alerts(
    severity: Optional[str] = Query(default=None, description="Filter by severity: info, warning, critical"),
    limit: int = Query(default=50, ge=1, le=500),
    since: Optional[datetime] = Query(default=None, description="ISO datetime; return alerts fired at or after this time"),
    db: Session = Depends(get_session),
):
    """Return alerts ordered by created_at desc."""
    query = db.query(AlertORM)
    if severity:
        query = query.filter(AlertORM.severity == severity)
    if since:
        since_utc = since if since.tzinfo is not None else since.replace(tzinfo=timezone.utc)
        query = query.filter(AlertORM.created_at >= since_utc)
    rows = query.order_by(AlertORM.created_at.desc()).limit(limit).all()
    return [AlertResponse.from_orm_row(r) for r in rows]


@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate(db: Session = Depends(get_session)):
    """Trigger a manual alert evaluation cycle."""
    alerts_fired = run_evaluation()
    return EvaluateResponse(evaluated=True, alerts_fired=alerts_fired)


@router.patch("/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge(alert_id: uuid.UUID, db: Session = Depends(get_session)):
    """Mark an alert as acknowledged (is_read=True)."""
    row = db.query(AlertORM).filter(AlertORM.id == alert_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    row.is_read = True
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return AlertResponse.from_orm_row(row)
