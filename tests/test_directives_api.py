"""Tests for the Directives REST API (APE-135).

Covers:
  POST  /api/directives
  GET   /api/directives
  GET   /api/directives/{id}
  PATCH /api/directives/{id}/cancel
  GET   /api/directives/{id}/status
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api import app
from src.data.database import get_session
from src.data.orm import Base, Directive as DirectiveORM


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_db_url(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("db") / "test_directives.duckdb"
    return f"duckdb:///{db_file}"


@pytest.fixture()
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
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.pop(get_session, None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _directive(
    title: str = "Test Directive",
    directive_type: str = "strategic",
    priority: str = "medium",
    owner: str = "alice",
    status: str = "pending",
    **kwargs,
) -> DirectiveORM:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    defaults = dict(
        id=uuid.uuid4(),
        title=title,
        directive_type=directive_type,
        priority=priority,
        owner=owner,
        status=status,
        due_date=None,
        notes=None,
        created_at=now,
        updated_at=now,
    )
    defaults.update(kwargs)
    return DirectiveORM(**defaults)


_SUBMIT_PAYLOAD = {
    "title": "Increase SEM budget Q3",
    "directive_type": "tactical",
    "priority": "high",
    "owner": "bob",
    "status": "pending",
}


# ---------------------------------------------------------------------------
# POST /api/directives
# ---------------------------------------------------------------------------

class TestSubmitDirective:
    def test_creates_directive(self, client):
        resp = client.post("/api/directives", json=_SUBMIT_PAYLOAD)
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == _SUBMIT_PAYLOAD["title"]
        assert body["directive_type"] == "tactical"
        assert body["priority"] == "high"
        assert body["owner"] == "bob"
        assert body["status"] == "pending"

    def test_response_has_id_and_timestamps(self, client):
        resp = client.post("/api/directives", json=_SUBMIT_PAYLOAD)
        assert resp.status_code == 201
        body = resp.json()
        assert "id" in body
        assert "created_at" in body
        assert "updated_at" in body
        uuid.UUID(body["id"])  # must be a valid UUID

    def test_optional_fields_default(self, client):
        payload = {
            "title": "Minimal directive",
            "directive_type": "operational",
            "owner": "charlie",
        }
        resp = client.post("/api/directives", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["priority"] == "medium"
        assert body["status"] == "pending"
        assert body["due_date"] is None
        assert body["notes"] is None

    def test_with_due_date_and_notes(self, client):
        payload = {**_SUBMIT_PAYLOAD, "due_date": "2026-06-30", "notes": "Urgent action needed"}
        resp = client.post("/api/directives", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["due_date"] == "2026-06-30"
        assert body["notes"] == "Urgent action needed"

    def test_persisted_to_db(self, client, db_session):
        payload = {**_SUBMIT_PAYLOAD, "title": "DB persist check"}
        resp = client.post("/api/directives", json=payload)
        assert resp.status_code == 201
        directive_id = uuid.UUID(resp.json()["id"])

        row = db_session.query(DirectiveORM).filter(DirectiveORM.id == directive_id).first()
        assert row is not None
        assert row.title == "DB persist check"


# ---------------------------------------------------------------------------
# GET /api/directives
# ---------------------------------------------------------------------------

class TestListDirectives:
    def test_empty_returns_empty_list(self, client):
        resp = client.get("/api/directives")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_all_directives(self, client, db_session):
        db_session.add_all([_directive(title="A"), _directive(title="B")])
        db_session.commit()

        resp = client.get("/api/directives")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_ordered_by_created_at_desc(self, client, db_session):
        from datetime import timedelta
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        older = _directive(title="Older", created_at=now - timedelta(hours=2), updated_at=now)
        newer = _directive(title="Newer", created_at=now, updated_at=now)
        db_session.add_all([older, newer])
        db_session.commit()

        resp = client.get("/api/directives")
        items = resp.json()
        assert items[0]["title"] == "Newer"
        assert items[1]["title"] == "Older"

    def test_filter_by_status(self, client, db_session):
        db_session.add_all([
            _directive(status="pending"),
            _directive(status="cancelled"),
            _directive(status="completed"),
        ])
        db_session.commit()

        resp = client.get("/api/directives?status=pending")
        assert resp.status_code == 200
        items = resp.json()
        assert all(i["status"] == "pending" for i in items)

    def test_filter_by_directive_type(self, client, db_session):
        db_session.add_all([
            _directive(directive_type="strategic"),
            _directive(directive_type="tactical"),
            _directive(directive_type="operational"),
        ])
        db_session.commit()

        resp = client.get("/api/directives?directive_type=tactical")
        assert resp.status_code == 200
        items = resp.json()
        assert all(i["directive_type"] == "tactical" for i in items)

    def test_filter_by_owner(self, client, db_session):
        db_session.add_all([
            _directive(owner="alice"),
            _directive(owner="bob"),
        ])
        db_session.commit()

        resp = client.get("/api/directives?owner=alice")
        assert resp.status_code == 200
        items = resp.json()
        assert all(i["owner"] == "alice" for i in items)

    def test_limit_param(self, client, db_session):
        for i in range(10):
            db_session.add(_directive(title=f"Dir {i}"))
        db_session.commit()

        resp = client.get("/api/directives?limit=3")
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_response_shape(self, client, db_session):
        db_session.add(_directive())
        db_session.commit()

        resp = client.get("/api/directives")
        item = resp.json()[0]
        for field in ("id", "title", "directive_type", "priority", "owner",
                      "due_date", "status", "notes", "created_at", "updated_at"):
            assert field in item, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# GET /api/directives/{id}
# ---------------------------------------------------------------------------

class TestGetDirective:
    def test_returns_directive(self, client, db_session):
        row = _directive(title="Detail test", owner="diana")
        db_session.add(row)
        db_session.commit()

        resp = client.get(f"/api/directives/{row.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Detail test"
        assert body["owner"] == "diana"
        assert str(body["id"]) == str(row.id)

    def test_404_for_unknown_id(self, client):
        resp = client.get(f"/api/directives/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_response_includes_all_fields(self, client, db_session):
        row = _directive(notes="Some notes", priority="high")
        db_session.add(row)
        db_session.commit()

        resp = client.get(f"/api/directives/{row.id}")
        body = resp.json()
        assert body["notes"] == "Some notes"
        assert body["priority"] == "high"


# ---------------------------------------------------------------------------
# PATCH /api/directives/{id}/cancel
# ---------------------------------------------------------------------------

class TestCancelDirective:
    def test_cancels_pending_directive(self, client, db_session):
        row = _directive(status="pending")
        db_session.add(row)
        db_session.commit()

        resp = client.patch(f"/api/directives/{row.id}/cancel")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "cancelled"
        assert str(body["id"]) == str(row.id)

    def test_cancel_idempotent(self, client, db_session):
        row = _directive(status="cancelled")
        db_session.add(row)
        db_session.commit()

        resp = client.patch(f"/api/directives/{row.id}/cancel")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_cancel_404_for_unknown_id(self, client):
        resp = client.patch(f"/api/directives/{uuid.uuid4()}/cancel")
        assert resp.status_code == 404

    def test_cancel_persists_to_db(self, client, db_session):
        row = _directive(status="pending")
        db_session.add(row)
        db_session.commit()

        client.patch(f"/api/directives/{row.id}/cancel")

        db_session.expire(row)
        db_session.refresh(row)
        assert row.status == "cancelled"


# ---------------------------------------------------------------------------
# GET /api/directives/{id}/status
# ---------------------------------------------------------------------------

class TestGetDirectiveStatus:
    def test_returns_status(self, client, db_session):
        row = _directive(status="pending")
        db_session.add(row)
        db_session.commit()

        resp = client.get(f"/api/directives/{row.id}/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "pending"
        assert str(body["id"]) == str(row.id)

    def test_only_id_and_status_in_response(self, client, db_session):
        row = _directive(status="pending")
        db_session.add(row)
        db_session.commit()

        resp = client.get(f"/api/directives/{row.id}/status")
        body = resp.json()
        assert set(body.keys()) == {"id", "status"}

    def test_status_404_for_unknown_id(self, client):
        resp = client.get(f"/api/directives/{uuid.uuid4()}/status")
        assert resp.status_code == 404

    def test_reflects_cancelled_status(self, client, db_session):
        row = _directive(status="cancelled")
        db_session.add(row)
        db_session.commit()

        resp = client.get(f"/api/directives/{row.id}/status")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"


# ---------------------------------------------------------------------------
# P1: Validation error paths (422 / 400 / 409)
# ---------------------------------------------------------------------------


class TestValidationErrorPaths:
    """P1 — error-path coverage: 422 from bad input, 409 from illegal transitions."""

    def test_invalid_status_enum_returns_422(self, client):
        """Submitting an unrecognised status value must return 422."""
        payload = {
            "title": "Bad status",
            "directive_type": "tactical",
            "owner": "tester",
            "status": "active",  # not in DirectiveStatus enum
        }
        resp = client.post("/api/directives", json=payload)
        assert resp.status_code == 422

    def test_rejected_status_returns_422(self, client):
        """'rejected' was removed from DirectiveStatus — must return 422."""
        payload = {
            "title": "Rejected status",
            "directive_type": "tactical",
            "owner": "tester",
            "status": "rejected",
        }
        resp = client.post("/api/directives", json=payload)
        assert resp.status_code == 422

    def test_malformed_payload_returns_422(self, client):
        """Empty parameters dict in DirectivePayload must trigger 422."""
        payload = {
            "title": "Bad payload",
            "directive_type": "tactical",
            "owner": "tester",
            "payload": {
                "type": "budget_reallocation",
                "parameters": {},  # must be non-empty
                "description": "test",
                "source_module": "spend_allocation",
            },
        }
        resp = client.post("/api/directives", json=payload)
        assert resp.status_code == 422

    def test_invalid_source_module_returns_422(self, client):
        """Unknown source_module in DirectivePayload must trigger 422."""
        payload = {
            "title": "Bad module",
            "directive_type": "tactical",
            "owner": "tester",
            "payload": {
                "type": "budget_reallocation",
                "parameters": {"amount": 100},
                "description": "test",
                "source_module": "unknown_module",
            },
        }
        resp = client.post("/api/directives", json=payload)
        assert resp.status_code == 422

    def test_valid_payload_accepted(self, client):
        """A well-formed DirectivePayload must be accepted and stored (201)."""
        payload = {
            "title": "Valid payload directive",
            "directive_type": "tactical",
            "owner": "tester",
            "payload": {
                "type": "budget_reallocation",
                "parameters": {"from_channel": "sem", "amount": 1000},
                "description": "Test reallocation",
                "source_module": "spend_allocation",
            },
        }
        resp = client.post("/api/directives", json=payload)
        assert resp.status_code == 201
        assert resp.json()["status"] == "pending"

    def test_cancel_completed_directive_returns_409(self, client, db_session):
        """Cancelling a completed directive must return 409 (state machine blocks it)."""
        row = _directive(status="completed")
        db_session.add(row)
        db_session.commit()

        resp = client.patch(f"/api/directives/{row.id}/cancel")
        assert resp.status_code == 409
        assert "completed" in resp.json()["detail"]

    def test_cancel_failed_directive_returns_409(self, client, db_session):
        """Cancelling a failed directive must return 409 (no outbound transitions)."""
        row = _directive(status="failed")
        db_session.add(row)
        db_session.commit()

        resp = client.patch(f"/api/directives/{row.id}/cancel")
        assert resp.status_code == 409
        assert "failed" in resp.json()["detail"]

    def test_cancel_in_progress_directive_returns_409(self, client, db_session):
        """in_progress → cancelled is not in the state machine; must return 409."""
        row = _directive(status="in_progress")
        db_session.add(row)
        db_session.commit()

        resp = client.patch(f"/api/directives/{row.id}/cancel")
        assert resp.status_code == 409

    def test_cancel_approved_directive_succeeds(self, client, db_session):
        """approved → cancelled is a valid transition; must return 200."""
        row = _directive(status="approved")
        db_session.add(row)
        db_session.commit()

        resp = client.patch(f"/api/directives/{row.id}/cancel")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"
