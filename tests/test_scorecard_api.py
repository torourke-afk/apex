"""Tests for scorecard API endpoints (APE-68).

Uses a temp-file DuckDB so tables persist across the single-engine lifetime.
Each test class gets one engine; each test gets its own session that is rolled
back (or the data is cleaned up) between runs.
"""

import os
import tempfile
import uuid
from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api import app
from src.data.database import get_session
from src.data.orm import Base, Alert, Budget, Campaign, FunnelEvent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def tmp_db_url(tmp_path_factory):
    """Return a file-based DuckDB URL for the test module."""
    db_file = tmp_path_factory.mktemp("db") / "test_apex.duckdb"
    return f"duckdb:///{db_file}"


@pytest.fixture(scope="module")
def db_engine(tmp_db_url):
    engine = create_engine(tmp_db_url, echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = Session()
    yield session
    # Clean up all rows inserted by the test
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()


@pytest.fixture()
def client(db_session):
    def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _campaign(**kwargs) -> Campaign:
    defaults = dict(
        id=uuid.uuid4(),
        name="Test Campaign",
        channel="search",
        status="active",
        spend=Decimal("5000.00"),
        revenue=Decimal("20000.00"),
        start_date=date.today().replace(day=1),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    defaults.update(kwargs)
    return Campaign(**defaults)


def _alert(severity="info", **kwargs) -> Alert:
    defaults = dict(
        id=uuid.uuid4(),
        title=f"{severity} alert",
        severity=severity,
        category="performance",
        message=f"Test {severity} message",
        is_read=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    defaults.update(kwargs)
    return Alert(**defaults)


def _budget(**kwargs) -> Budget:
    defaults = dict(
        id=uuid.uuid4(),
        name="MTD Budget",
        channel="display",
        period="monthly",
        period_start=date.today().replace(day=1),
        allocated=Decimal("12000.00"),
        actual=Decimal("10000.00"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    defaults.update(kwargs)
    return Budget(**defaults)


# ---------------------------------------------------------------------------
# /api/scorecard/kpis
# ---------------------------------------------------------------------------

class TestKPIs:
    def test_empty_db_returns_valid_response(self, client):
        resp = client.get("/api/scorecard/kpis")
        assert resp.status_code == 200
        body = resp.json()
        assert "kpis" in body
        assert "as_of" in body
        assert isinstance(body["kpis"], list)

    def test_returns_exactly_7_spec_kpis(self, client):
        resp = client.get("/api/scorecard/kpis")
        assert resp.status_code == 200
        kpis = resp.json()["kpis"]
        names = [k["name"] for k in kpis]
        assert names == [
            "Net Household Growth",
            "MOB6 Retention Rate",
            "Brand Capture Rate",
            "CPIHH",
            "LLM Visibility Score",
            "App Completion Rate",
            "Onboarding Activation Day 30",
        ]

    def test_kpis_have_required_fields(self, client):
        resp = client.get("/api/scorecard/kpis")
        assert resp.status_code == 200
        kpis = resp.json()["kpis"]
        assert len(kpis) == 7
        for kpi in kpis:
            assert "name" in kpi
            assert "value" in kpi
            assert "target" in kpi
            assert "delta" in kpi
            assert "delta_pct" in kpi
            assert "sparkline_data" in kpi
            assert kpi["trend"] in ("improving", "declining", "flat")

    def test_trend_field_valid_literal(self, client):
        resp = client.get("/api/scorecard/kpis")
        assert resp.status_code == 200
        for kpi in resp.json()["kpis"]:
            assert kpi["trend"] in ("improving", "declining", "flat")

    def test_sparkline_data_is_list_of_floats(self, client):
        resp = client.get("/api/scorecard/kpis")
        assert resp.status_code == 200
        for kpi in resp.json()["kpis"]:
            assert isinstance(kpi["sparkline_data"], list)
            for pt in kpi["sparkline_data"]:
                assert isinstance(pt, (int, float))


# ---------------------------------------------------------------------------
# /api/scorecard/financial-summary
# ---------------------------------------------------------------------------

class TestFinancialSummary:
    def test_empty_db_returns_zeros(self, client):
        resp = client.get("/api/scorecard/financial-summary")
        assert resp.status_code == 200
        body = resp.json()
        assert Decimal(body["media_spend_mtd"]) == Decimal("0")
        assert Decimal(body["media_spend_ytd"]) == Decimal("0")
        assert body["brand_burn_rate"] == 0.0

    def test_required_fields_present(self, client):
        resp = client.get("/api/scorecard/financial-summary")
        assert resp.status_code == 200
        body = resp.json()
        required = [
            "media_spend_mtd", "media_spend_qtd", "media_spend_ytd",
            "spend_vs_plan_mtd", "spend_vs_plan_qtd", "spend_vs_plan_ytd",
            "blended_cpl", "blended_cpihh", "cpl_trend", "cpihh_trend",
            "revenue_attribution", "brand_burn_rate", "incremental_spend_vs_budget",
        ]
        for field in required:
            assert field in body, f"Missing field: {field}"

    def test_trend_literals_valid(self, client):
        resp = client.get("/api/scorecard/financial-summary")
        assert resp.status_code == 200
        body = resp.json()
        assert body["cpl_trend"] in ("improving", "declining", "flat")
        assert body["cpihh_trend"] in ("improving", "declining", "flat")

    def test_spend_reflects_campaigns(self, client, db_session):
        db_session.add(_campaign(spend=Decimal("10000.00"), revenue=Decimal("40000.00")))
        db_session.commit()

        resp = client.get("/api/scorecard/financial-summary")
        assert resp.status_code == 200
        body = resp.json()
        assert Decimal(body["media_spend_mtd"]) > 0

    def test_vs_plan_negative_when_under_budget(self, client, db_session):
        db_session.add(_campaign(spend=Decimal("10000.00"), revenue=Decimal("40000.00")))
        db_session.add(_budget(allocated=Decimal("12000.00")))
        db_session.commit()

        resp = client.get("/api/scorecard/financial-summary")
        assert resp.status_code == 200
        body = resp.json()
        assert Decimal(body["spend_vs_plan_mtd"]) < 0


# ---------------------------------------------------------------------------
# /api/scorecard/alerts
# ---------------------------------------------------------------------------

class TestAlerts:
    def test_empty_db_returns_empty_list(self, client):
        resp = client.get("/api/scorecard/alerts")
        assert resp.status_code == 200
        body = resp.json()
        assert body["alerts"] == []
        assert body["total_count"] == 0

    def test_returns_alerts(self, client, db_session):
        for severity in ("error", "warning", "info"):
            db_session.add(_alert(severity=severity))
        db_session.commit()

        resp = client.get("/api/scorecard/alerts")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_count"] == 3
        assert len(body["alerts"]) == 3

    def test_severity_filter(self, client, db_session):
        for severity in ("error", "warning", "info"):
            db_session.add(_alert(severity=severity))
        db_session.commit()

        resp = client.get("/api/scorecard/alerts?severity=error")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_count"] == 1
        assert body["alerts"][0]["severity"] == "error"

    def test_limit_param(self, client, db_session):
        for i in range(15):
            db_session.add(_alert(severity="info", title=f"Alert {i}", message=f"Msg {i}"))
        db_session.commit()

        resp = client.get("/api/scorecard/alerts?limit=5")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["alerts"]) == 5
        assert body["total_count"] == 15

    def test_alert_fields(self, client, db_session):
        db_session.add(_alert(severity="warning", category="budget", message="Budget exceeded"))
        db_session.commit()

        resp = client.get("/api/scorecard/alerts")
        assert resp.status_code == 200
        alert = resp.json()["alerts"][0]
        assert "severity" in alert
        assert "kpi_name" in alert
        assert "description" in alert
        assert "created_at" in alert
        assert "module_link" in alert
        assert alert["severity"] in ("error", "warning", "info")
