"""Alert Engine — AlertRule dataclass and evaluation logic.

Supports three condition types:
  - threshold: fires when current value crosses a threshold (above/below)
  - trend: fires when linear-regression slope over lookback period crosses threshold
  - anomaly: fires when current value deviates > 2 std dev from rolling mean
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import sqlalchemy as sa

from src.data.database import engine
from src.data.orm import Alert as AlertORM


# ---------------------------------------------------------------------------
# AlertRule dataclass
# ---------------------------------------------------------------------------

@dataclass
class AlertRule:
    kpi_name: str
    condition_type: str          # "threshold" | "trend" | "anomaly"
    threshold_value: float
    lookback_period: int         # number of periods
    severity: str                # "critical" | "warning" | "info"
    active: bool = True
    # For threshold rules: "above" | "below"
    condition_direction: str = "below"


# ---------------------------------------------------------------------------
# FiredAlert output dataclass
# ---------------------------------------------------------------------------

@dataclass
class FiredAlert:
    rule_name: str
    kpi_name: str
    severity: str
    condition_type: str
    current_value: float
    threshold_value: float
    message: str
    fired_at: str                # ISO timestamp
    acknowledged: bool = False


# ---------------------------------------------------------------------------
# Default alert rules
# ---------------------------------------------------------------------------

DEFAULT_ALERT_RULES: list[AlertRule] = [
    AlertRule(
        kpi_name="Net HH Growth",
        condition_type="threshold",
        threshold_value=0.95,
        lookback_period=1,
        severity="critical",
        condition_direction="below",
    ),
    AlertRule(
        kpi_name="MOB6 Retention",
        condition_type="threshold",
        threshold_value=-2.0,
        lookback_period=1,
        severity="critical",
        condition_direction="below",
    ),
    AlertRule(
        kpi_name="Brand Capture Rate",
        condition_type="trend",
        threshold_value=-5.0,
        lookback_period=3,
        severity="warning",
        condition_direction="below",
    ),
    AlertRule(
        kpi_name="CPIHH",
        condition_type="trend",
        threshold_value=0.10,
        lookback_period=4,
        severity="warning",
        condition_direction="above",
    ),
    AlertRule(
        kpi_name="LLM Visibility",
        condition_type="trend",
        threshold_value=-5.0,
        lookback_period=3,
        severity="warning",
        condition_direction="below",
    ),
    AlertRule(
        kpi_name="App Completion Rate",
        condition_type="trend",
        threshold_value=-3.0,
        lookback_period=4,
        severity="warning",
        condition_direction="below",
    ),
    AlertRule(
        kpi_name="SEM CPC (non-branded)",
        condition_type="threshold",
        threshold_value=5.00,
        lookback_period=1,
        severity="warning",
        condition_direction="above",
    ),
    AlertRule(
        kpi_name="SEM Quality Score",
        condition_type="threshold",
        threshold_value=5.0,
        lookback_period=1,
        severity="info",
        condition_direction="below",
    ),
    AlertRule(
        kpi_name="Impression Share (branded)",
        condition_type="threshold",
        threshold_value=85.0,
        lookback_period=1,
        severity="warning",
        condition_direction="below",
    ),
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _linreg_slope(values: list[float]) -> float:
    """Return the OLS slope for the sequence values (x = index)."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return num / den if den else 0.0


def _rule_name(rule: AlertRule) -> str:
    return f"{rule.kpi_name}:{rule.condition_type}:{rule.condition_direction}"


def _existing_active(kpi_name: str, condition_type: str) -> bool:
    """Return True if any active (unresolved) alert already exists for this KPI+condition.

    Acknowledged (is_read=true) alerts are still considered active until resolved,
    so re-evaluation skips them — preventing re-fire after acknowledgment.
    """
    title_prefix = f"[{condition_type.upper()}] {kpi_name}"
    with engine.connect() as conn:
        row = conn.execute(
            sa.text(
                "SELECT id FROM alerts "
                "WHERE title LIKE :prefix "
                "AND resolved_at IS NULL "
                "LIMIT 1"
            ),
            {"prefix": f"{title_prefix}%"},
        ).fetchone()
    return row is not None


def _write_alert_to_db(fired: FiredAlert) -> None:
    """Persist a FiredAlert to the alerts table."""
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO alerts (id, title, severity, category, message, is_read, created_at, updated_at) "
                "VALUES (:id, :title, :severity, :category, :message, false, :now, :now)"
            ),
            {
                "id": uuid.uuid4(),
                "title": f"[{fired.condition_type.upper()}] {fired.kpi_name}",
                "severity": fired.severity,
                "category": "performance",
                "message": fired.message,
                "now": datetime.now(timezone.utc),
            },
        )


# ---------------------------------------------------------------------------
# Main evaluation function
# ---------------------------------------------------------------------------

def evaluate_alerts(
    current_metrics: dict[str, Any],
    historical_metrics: list[dict[str, Any]],
    rules: list[AlertRule],
) -> list[FiredAlert]:
    """Evaluate all active alert rules and return a list of fired alerts.

    Args:
        current_metrics:    {kpi_name: current_value} for the latest period.
        historical_metrics: Ordered list of metric dicts (oldest → newest),
                            each with the same shape as current_metrics.
                            Does NOT include current_metrics.
        rules:              List of AlertRule objects to evaluate.

    Returns:
        List of FiredAlert dataclasses for every rule that fired.
        Fired alerts are also written to the DB (idempotent: skips if an
        unacknowledged alert already exists for that KPI+condition).
    """
    fired: list[FiredAlert] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for rule in rules:
        if not rule.active:
            continue

        kpi = rule.kpi_name
        current_value = current_metrics.get(kpi)
        if current_value is None:
            continue

        try:
            current_value = float(current_value)
        except (TypeError, ValueError):
            continue

        alert: FiredAlert | None = None

        # ------------------------------------------------------------------
        # Threshold condition
        # ------------------------------------------------------------------
        if rule.condition_type == "threshold":
            triggered = (
                current_value < rule.threshold_value
                if rule.condition_direction == "below"
                else current_value > rule.threshold_value
            )
            if triggered:
                direction_word = "below" if rule.condition_direction == "below" else "above"
                alert = FiredAlert(
                    rule_name=_rule_name(rule),
                    kpi_name=kpi,
                    severity=rule.severity,
                    condition_type=rule.condition_type,
                    current_value=current_value,
                    threshold_value=rule.threshold_value,
                    message=(
                        f"{kpi} is {current_value:.4g}, which is {direction_word} "
                        f"the threshold of {rule.threshold_value:.4g}."
                    ),
                    fired_at=now_iso,
                )

        # ------------------------------------------------------------------
        # Trend condition (linear regression slope)
        # ------------------------------------------------------------------
        elif rule.condition_type == "trend":
            lookback = rule.lookback_period
            history_values: list[float] = []
            for h in historical_metrics[-(lookback - 1):]:
                v = h.get(kpi)
                if v is not None:
                    try:
                        history_values.append(float(v))
                    except (TypeError, ValueError):
                        pass
            history_values.append(current_value)

            if len(history_values) >= 2:
                slope = _linreg_slope(history_values)
                triggered = (
                    slope < rule.threshold_value
                    if rule.condition_direction == "below"
                    else slope > rule.threshold_value
                )
                if triggered:
                    direction_word = "declining" if rule.condition_direction == "below" else "increasing"
                    alert = FiredAlert(
                        rule_name=_rule_name(rule),
                        kpi_name=kpi,
                        severity=rule.severity,
                        condition_type=rule.condition_type,
                        current_value=slope,
                        threshold_value=rule.threshold_value,
                        message=(
                            f"{kpi} trend slope is {slope:.4g} over {lookback} periods, "
                            f"which is {direction_word} beyond threshold {rule.threshold_value:.4g}."
                        ),
                        fired_at=now_iso,
                    )

        # ------------------------------------------------------------------
        # Anomaly condition (rolling mean ± 2 std dev)
        # ------------------------------------------------------------------
        elif rule.condition_type == "anomaly":
            lookback = rule.lookback_period
            history_values = []
            for h in historical_metrics[-lookback:]:
                v = h.get(kpi)
                if v is not None:
                    try:
                        history_values.append(float(v))
                    except (TypeError, ValueError):
                        pass

            if len(history_values) >= 2:
                mean = sum(history_values) / len(history_values)
                variance = sum((x - mean) ** 2 for x in history_values) / len(history_values)
                std = math.sqrt(variance)
                z_score = (current_value - mean) / std if std > 0 else 0.0
                if abs(z_score) > 2.0:
                    direction = "above" if z_score > 0 else "below"
                    alert = FiredAlert(
                        rule_name=_rule_name(rule),
                        kpi_name=kpi,
                        severity=rule.severity,
                        condition_type=rule.condition_type,
                        current_value=current_value,
                        threshold_value=rule.threshold_value,
                        message=(
                            f"{kpi} value {current_value:.4g} is {direction} the rolling mean "
                            f"by {abs(z_score):.2f} std deviations (mean={mean:.4g}, std={std:.4g})."
                        ),
                        fired_at=now_iso,
                    )

        # ------------------------------------------------------------------
        # Idempotency check + DB write
        # ------------------------------------------------------------------
        if alert is not None:
            if not _existing_active(kpi, rule.condition_type):
                _write_alert_to_db(alert)
                fired.append(alert)

    return fired
