"""Tests for src/data/alert_engine.py.

Uses an in-memory DuckDB engine (monkeypatched) so no live database is required.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text

import src.data.alert_engine as engine_module
from src.data.alert_engine import (
    AlertRule,
    DEFAULT_ALERT_RULES,
    FiredAlert,
    _linreg_slope,
    evaluate_alerts,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mem_engine(monkeypatch):
    """Patch alert_engine.engine with a fresh in-memory DuckDB for each test."""
    eng = create_engine("duckdb:///:memory:", echo=False)
    with eng.begin() as conn:
        conn.execute(text("""
            CREATE TABLE alerts (
                id UUID PRIMARY KEY,
                title VARCHAR NOT NULL,
                severity VARCHAR NOT NULL DEFAULT 'info',
                category VARCHAR NOT NULL,
                message TEXT NOT NULL,
                is_read BOOLEAN NOT NULL DEFAULT false,
                resolved_at TIMESTAMP,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """))
    monkeypatch.setattr(engine_module, "engine", eng)
    return eng


# ---------------------------------------------------------------------------
# Unit: _linreg_slope
# ---------------------------------------------------------------------------

def test_linreg_slope_positive():
    assert _linreg_slope([1.0, 2.0, 3.0]) == pytest.approx(1.0)


def test_linreg_slope_negative():
    assert _linreg_slope([3.0, 2.0, 1.0]) == pytest.approx(-1.0)


def test_linreg_slope_flat():
    assert _linreg_slope([5.0, 5.0, 5.0]) == pytest.approx(0.0)


def test_linreg_slope_single_point():
    assert _linreg_slope([42.0]) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Threshold condition
# ---------------------------------------------------------------------------

def test_threshold_below_fires():
    rule = AlertRule(
        kpi_name="Net HH Growth",
        condition_type="threshold",
        threshold_value=0.95,
        lookback_period=1,
        severity="critical",
        condition_direction="below",
    )
    alerts = evaluate_alerts({"Net HH Growth": 0.90}, [], [rule])
    assert len(alerts) == 1
    assert alerts[0].kpi_name == "Net HH Growth"
    assert alerts[0].severity == "critical"
    assert alerts[0].condition_type == "threshold"
    assert alerts[0].current_value == pytest.approx(0.90)


def test_threshold_below_no_fire_when_equal():
    rule = AlertRule(
        kpi_name="Net HH Growth",
        condition_type="threshold",
        threshold_value=0.95,
        lookback_period=1,
        severity="critical",
        condition_direction="below",
    )
    alerts = evaluate_alerts({"Net HH Growth": 0.95}, [], [rule])
    assert alerts == []


def test_threshold_above_fires():
    rule = AlertRule(
        kpi_name="SEM CPC (non-branded)",
        condition_type="threshold",
        threshold_value=5.00,
        lookback_period=1,
        severity="warning",
        condition_direction="above",
    )
    alerts = evaluate_alerts({"SEM CPC (non-branded)": 6.50}, [], [rule])
    assert len(alerts) == 1
    assert alerts[0].current_value == pytest.approx(6.50)


def test_threshold_above_no_fire_when_below():
    rule = AlertRule(
        kpi_name="SEM CPC (non-branded)",
        condition_type="threshold",
        threshold_value=5.00,
        lookback_period=1,
        severity="warning",
        condition_direction="above",
    )
    alerts = evaluate_alerts({"SEM CPC (non-branded)": 4.00}, [], [rule])
    assert alerts == []


# ---------------------------------------------------------------------------
# Trend condition
# ---------------------------------------------------------------------------

def test_trend_decline_fires():
    rule = AlertRule(
        kpi_name="Brand Capture Rate",
        condition_type="trend",
        threshold_value=-5.0,
        lookback_period=3,
        severity="warning",
        condition_direction="below",
    )
    history = [{"Brand Capture Rate": 70}, {"Brand Capture Rate": 60}]
    current = {"Brand Capture Rate": 50}
    alerts = evaluate_alerts(current, history, [rule])
    assert len(alerts) == 1
    assert alerts[0].condition_type == "trend"
    # slope should be ~ -10
    assert alerts[0].current_value < -5.0


def test_trend_no_fire_when_flat():
    rule = AlertRule(
        kpi_name="Brand Capture Rate",
        condition_type="trend",
        threshold_value=-5.0,
        lookback_period=3,
        severity="warning",
        condition_direction="below",
    )
    history = [{"Brand Capture Rate": 70}, {"Brand Capture Rate": 70}]
    current = {"Brand Capture Rate": 70}
    alerts = evaluate_alerts(current, history, [rule])
    assert alerts == []


def test_trend_increase_fires():
    rule = AlertRule(
        kpi_name="CPIHH",
        condition_type="trend",
        threshold_value=0.10,
        lookback_period=3,
        severity="warning",
        condition_direction="above",
    )
    # slope = 0.15 (steeper than 0.10 threshold) → should fire
    history = [{"CPIHH": 1.00}, {"CPIHH": 1.15}]
    current = {"CPIHH": 1.30}
    alerts = evaluate_alerts(current, history, [rule])
    assert len(alerts) == 1
    assert alerts[0].current_value > 0.10


# ---------------------------------------------------------------------------
# Anomaly condition
# ---------------------------------------------------------------------------

def test_anomaly_fires_on_spike():
    rule = AlertRule(
        kpi_name="App Completion Rate",
        condition_type="anomaly",
        threshold_value=0.0,
        lookback_period=5,
        severity="warning",
        condition_direction="above",
    )
    # mean=50, std=0 … give some variance
    history = [
        {"App Completion Rate": 48},
        {"App Completion Rate": 50},
        {"App Completion Rate": 52},
        {"App Completion Rate": 49},
        {"App Completion Rate": 51},
    ]
    current = {"App Completion Rate": 100}  # far above mean
    alerts = evaluate_alerts(current, history, [rule])
    assert len(alerts) == 1
    assert "std deviations" in alerts[0].message


def test_anomaly_no_fire_within_2_std():
    rule = AlertRule(
        kpi_name="App Completion Rate",
        condition_type="anomaly",
        threshold_value=0.0,
        lookback_period=5,
        severity="warning",
        condition_direction="above",
    )
    history = [
        {"App Completion Rate": 48},
        {"App Completion Rate": 50},
        {"App Completion Rate": 52},
        {"App Completion Rate": 49},
        {"App Completion Rate": 51},
    ]
    current = {"App Completion Rate": 51}
    alerts = evaluate_alerts(current, history, [rule])
    assert alerts == []


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

def test_idempotency_does_not_refire(mem_engine):
    rule = AlertRule(
        kpi_name="SEM Quality Score",
        condition_type="threshold",
        threshold_value=5.0,
        lookback_period=1,
        severity="info",
        condition_direction="below",
    )
    current = {"SEM Quality Score": 3.0}
    first = evaluate_alerts(current, [], [rule])
    assert len(first) == 1

    # Same condition, unacknowledged alert already exists → should NOT refire
    second = evaluate_alerts(current, [], [rule])
    assert second == []


def test_acknowledged_alert_not_refired(mem_engine):
    """Acknowledged (is_read=true) alerts must NOT trigger a new fire on re-evaluation.

    An acknowledged alert is still unresolved, so the engine should treat it as
    active and suppress re-firing — matching the acceptance criterion.
    """
    rule = AlertRule(
        kpi_name="SEM Quality Score",
        condition_type="threshold",
        threshold_value=5.0,
        lookback_period=1,
        severity="info",
        condition_direction="below",
    )
    current = {"SEM Quality Score": 3.0}
    first = evaluate_alerts(current, [], [rule])
    assert len(first) == 1

    # Acknowledge (mark as read) the existing alert — it remains unresolved
    with mem_engine.begin() as conn:
        conn.execute(text("UPDATE alerts SET is_read = true"))

    # Re-evaluation must NOT produce a new alert (acknowledged ≠ resolved)
    second = evaluate_alerts(current, [], [rule])
    assert second == []


# ---------------------------------------------------------------------------
# Inactive rules
# ---------------------------------------------------------------------------

def test_inactive_rule_does_not_fire():
    rule = AlertRule(
        kpi_name="Net HH Growth",
        condition_type="threshold",
        threshold_value=0.95,
        lookback_period=1,
        severity="critical",
        condition_direction="below",
        active=False,
    )
    alerts = evaluate_alerts({"Net HH Growth": 0.50}, [], [rule])
    assert alerts == []


# ---------------------------------------------------------------------------
# Missing KPI in current metrics
# ---------------------------------------------------------------------------

def test_missing_kpi_skipped():
    rule = AlertRule(
        kpi_name="Net HH Growth",
        condition_type="threshold",
        threshold_value=0.95,
        lookback_period=1,
        severity="critical",
        condition_direction="below",
    )
    alerts = evaluate_alerts({}, [], [rule])
    assert alerts == []


# ---------------------------------------------------------------------------
# DEFAULT_ALERT_RULES
# ---------------------------------------------------------------------------

def test_default_rules_count():
    assert len(DEFAULT_ALERT_RULES) == 9


def test_default_rules_kpi_names():
    expected = {
        "Net HH Growth",
        "MOB6 Retention",
        "Brand Capture Rate",
        "CPIHH",
        "LLM Visibility",
        "App Completion Rate",
        "SEM CPC (non-branded)",
        "SEM Quality Score",
        "Impression Share (branded)",
    }
    actual = {r.kpi_name for r in DEFAULT_ALERT_RULES}
    assert actual == expected


def test_default_rules_severities():
    critical = [r for r in DEFAULT_ALERT_RULES if r.severity == "critical"]
    warning = [r for r in DEFAULT_ALERT_RULES if r.severity == "warning"]
    info = [r for r in DEFAULT_ALERT_RULES if r.severity == "info"]
    assert len(critical) == 2
    assert len(warning) == 6
    assert len(info) == 1


def test_default_rules_condition_types():
    types = {r.condition_type for r in DEFAULT_ALERT_RULES}
    assert "threshold" in types
    assert "trend" in types


# ---------------------------------------------------------------------------
# Integration: seed data evaluation
# ---------------------------------------------------------------------------

def test_seed_data_triggers_at_least_3_alerts(mem_engine):
    """Running evaluation against crafted seed data produces >= 3 alerts
    spanning at least two condition types (threshold + trend), satisfying the
    acceptance criterion that >= 3 alert types fire from seed data."""
    # Construct deterministic metrics that trip three different default rules:
    #   1. threshold/above — SEM CPC (non-branded) 6.00 > threshold 5.00
    #   2. threshold/below — Impression Share (branded) 78 < threshold 85
    #   3. trend/below     — App Completion Rate slope ≈ -10 < threshold -3.0
    # All other KPIs are given safe values to avoid spurious alerts.
    historical = [
        {"App Completion Rate": 80.0},
        {"App Completion Rate": 70.0},
        {"App Completion Rate": 60.0},
    ]
    current = {
        "SEM CPC (non-branded)":      6.00,   # fires: above 5.00
        "Impression Share (branded)": 78.0,   # fires: below 85.0
        "App Completion Rate":        50.0,   # fires: trend slope ≈ -10 < -3.0
        # Safe values — will not trip any rule
        "Net HH Growth":              12000.0,
        "MOB6 Retention":             84.0,
        "Brand Capture Rate":         39.0,
        "CPIHH":                      320.0,
        "LLM Visibility":             60.0,
        "SEM Quality Score":          7.0,
    }
    alerts = evaluate_alerts(current, historical, DEFAULT_ALERT_RULES)
    assert len(alerts) >= 3, (
        f"Expected >= 3 alerts from seed data, got {len(alerts)}: "
        + ", ".join(f"{a.kpi_name}({a.condition_type})" for a in alerts)
    )
    condition_types_fired = {a.condition_type for a in alerts}
    assert "threshold" in condition_types_fired
    assert "trend" in condition_types_fired


def test_alert_persistence(mem_engine):
    """Fired alerts are persisted to the alerts table and are retrievable."""
    rule = AlertRule(
        kpi_name="SEM CPC (non-branded)",
        condition_type="threshold",
        threshold_value=5.00,
        lookback_period=1,
        severity="warning",
        condition_direction="above",
    )
    fired = evaluate_alerts({"SEM CPC (non-branded)": 6.00}, [], [rule])
    assert len(fired) == 1

    with mem_engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id, title, severity FROM alerts")
        ).fetchall()
    assert len(rows) == 1
    assert "SEM CPC" in rows[0].title
    assert rows[0].severity == "warning"


def test_fired_alert_has_iso_timestamp():
    rule = AlertRule(
        kpi_name="SEM Quality Score",
        condition_type="threshold",
        threshold_value=5.0,
        lookback_period=1,
        severity="info",
        condition_direction="below",
    )
    alerts = evaluate_alerts({"SEM Quality Score": 3.0}, [], [rule])
    assert len(alerts) == 1
    # Should parse as ISO datetime without error
    datetime.fromisoformat(alerts[0].fired_at)
    assert alerts[0].acknowledged is False
