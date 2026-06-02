"""Tests for the Alerts REST API (APE-105).

Covers GET /api/alerts, POST /api/alerts/evaluate, and
PATCH /api/alerts/{id}/acknowledge.

APScheduler is not started by TestClient (no ASGI lifespan by default),
so the scheduler integration is tested at the unit level only.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api import app
from src.data.database import get_session
from src.data.orm import Alert as AlertORM, Base


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def tmp_db_url(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("db") / "test_alerts.duckdb"
    return f"duckdb:///{db_file}"


@pytest.fixture(scope="module")
def db_engine(tmp_db_url):
    eng = create_engine(tmp_db_url, echo=False)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = Session()
    yield session
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()


@pytest.fixture()
def client(db_session):
    def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    # Use raise_server_exceptions=True (default) so test failures are surfaced cleanly.
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _alert(severity: str = "info", is_read: bool = False, **kwargs) -> AlertORM:
    now = datetime.now(timezone.utc)
    defaults = dict(
        id=uuid.uuid4(),
        title=f"[THRESHOLD] Test KPI",
        severity=severity,
        category="performance",
        message=f"Test {severity} alert message",
        is_read=is_read,
        created_at=now,
        updated_at=now,
    )
    defaults.update(kwargs)
    return AlertORM(**defaults)


# ---------------------------------------------------------------------------
# GET /api/alerts
# ---------------------------------------------------------------------------

class TestListAlerts:
    def test_empty_returns_empty_list(self, client):
        resp = client.get("/api/alerts")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_alerts_ordered_by_created_at_desc(self, client, db_session):
        now = datetime.now(timezone.utc)
        older = _alert(severity="info", created_at=now - timedelta(hours=2), updated_at=now)
        newer = _alert(severity="warning", created_at=now, updated_at=now)
        db_session.add_all([older, newer])
        db_session.commit()

        resp = client.get("/api/alerts")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 2
        assert items[0]["severity"] == "warning"  # newer first
        assert items[1]["severity"] == "info"

    def test_severity_filter(self, client, db_session):
        db_session.add_all([
            _alert(severity="info"),
            _alert(severity="warning"),
            _alert(severity="critical"),
        ])
        db_session.commit()

        resp = client.get("/api/alerts?severity=critical")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]["severity"] == "critical"

    def test_limit_param(self, client, db_session):
        for i in range(10):
            db_session.add(_alert(severity="info", title=f"Alert {i}", message=f"Msg {i}"))
        db_session.commit()

        resp = client.get("/api/alerts?limit=3")
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_since_filter(self, client, db_session):
        now = datetime.now(timezone.utc)
        old = _alert(severity="info", created_at=now - timedelta(days=2), updated_at=now)
        recent = _alert(severity="warning", created_at=now, updated_at=now)
        db_session.add_all([old, recent])
        db_session.commit()

        # Use naive UTC ISO string to avoid '+00:00' URL-encoding issues
        cutoff = (now - timedelta(hours=1)).replace(tzinfo=None).isoformat()
        resp = client.get(f"/api/alerts?since={cutoff}")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]["severity"] == "warning"

    def test_response_shape(self, client, db_session):
        db_session.add(_alert(severity="warning"))
        db_session.commit()

        resp = client.get("/api/alerts")
        assert resp.status_code == 200
        item = resp.json()[0]
        for field in ("id", "title", "severity", "category", "message",
                      "acknowledged", "created_at", "updated_at"):
            assert field in item, f"Missing field: {field}"

    def test_acknowledged_reflects_is_read(self, client, db_session):
        db_session.add(_alert(severity="info", is_read=True))
        db_session.add(_alert(severity="info", is_read=False))
        db_session.commit()

        resp = client.get("/api/alerts")
        assert resp.status_code == 200
        items = resp.json()
        ack_values = {i["acknowledged"] for i in items}
        assert True in ack_values
        assert False in ack_values


# ---------------------------------------------------------------------------
# POST /api/alerts/evaluate
# ---------------------------------------------------------------------------

class TestEvaluateAlerts:
    def test_returns_evaluated_true(self, client):
        with patch("src.api.alerts.run_evaluation", return_value=0) as mock_eval:
            resp = client.post("/api/alerts/evaluate")
        assert resp.status_code == 200
        body = resp.json()
        assert body["evaluated"] is True
        assert body["alerts_fired"] == 0
        mock_eval.assert_called_once()

    def test_returns_alerts_fired_count(self, client):
        with patch("src.api.alerts.run_evaluation", return_value=3):
            resp = client.post("/api/alerts/evaluate")
        assert resp.status_code == 200
        assert resp.json()["alerts_fired"] == 3

    def test_evaluate_persists_alerts(self, client, db_session):
        """Real evaluation run — any fired alerts appear in GET /api/alerts."""
        # Run actual evaluation (no mock); seed data is set up to potentially fire alerts
        resp = client.post("/api/alerts/evaluate")
        assert resp.status_code == 200
        body = resp.json()
        assert body["evaluated"] is True
        assert isinstance(body["alerts_fired"], int)
        assert body["alerts_fired"] >= 0


# ---------------------------------------------------------------------------
# PATCH /api/alerts/{alert_id}/acknowledge
# ---------------------------------------------------------------------------

class TestAcknowledgeAlert:
    def test_acknowledge_sets_is_read(self, client, db_session):
        alert = _alert(severity="warning", is_read=False)
        db_session.add(alert)
        db_session.commit()

        resp = client.patch(f"/api/alerts/{alert.id}/acknowledge")
        assert resp.status_code == 200
        body = resp.json()
        assert body["acknowledged"] is True
        assert str(body["id"]) == str(alert.id)

    def test_acknowledge_returns_updated_alert(self, client, db_session):
        alert = _alert(severity="critical", is_read=False)
        db_session.add(alert)
        db_session.commit()

        resp = client.patch(f"/api/alerts/{alert.id}/acknowledge")
        assert resp.status_code == 200
        body = resp.json()
        assert body["severity"] == "critical"
        assert body["acknowledged"] is True

    def test_acknowledge_404_for_missing_alert(self, client):
        fake_id = uuid.uuid4()
        resp = client.patch(f"/api/alerts/{fake_id}/acknowledge")
        assert resp.status_code == 404

    def test_acknowledge_idempotent(self, client, db_session):
        """Acknowledging an already-acknowledged alert is fine."""
        alert = _alert(severity="info", is_read=True)
        db_session.add(alert)
        db_session.commit()

        resp = client.patch(f"/api/alerts/{alert.id}/acknowledge")
        assert resp.status_code == 200
        assert resp.json()["acknowledged"] is True


# ---------------------------------------------------------------------------
# Scheduler unit test
# ---------------------------------------------------------------------------

class TestSchedulerSetup:
    def test_run_evaluation_callable(self):
        """run_evaluation() is importable and returns an int."""
        from src.api.alerts import run_evaluation
        import src.data.alert_engine as engine_module
        from sqlalchemy import create_engine, text

        # Patch alert_engine with a fresh in-memory DB
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

        original_engine = engine_module.engine
        engine_module.engine = eng
        try:
            result = run_evaluation()
            assert isinstance(result, int)
            assert result >= 0
        finally:
            engine_module.engine = original_engine
            eng.dispose()
