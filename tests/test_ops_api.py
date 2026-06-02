"""Tests for Ops REST API endpoints (APE-118).

Covers all 7 endpoints:
  GET  /api/ops/calendar
  GET  /api/ops/capacity
  GET  /api/ops/approvals
  POST /api/ops/approvals/{id}/approve
  POST /api/ops/approvals/{id}/reject
  GET  /api/ops/health
  GET  /api/ops/competitive-feed

Calendar, capacity, health, and competitive-feed are backed by seed data and
require no database fixtures.  Approvals use the Directive ORM table so those
tests use an isolated in-memory DuckDB instance.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api import app
from src.data.database import get_session
from src.data.orm import Base


# ---------------------------------------------------------------------------
# DB fixtures (for approval tests)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def tmp_db_url(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("db") / "test_ops.duckdb"
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
    def override():
        yield db_session

    app.dependency_overrides[get_session] = override
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# Seed-only client (no DB override needed — endpoints don't hit DB)
@pytest.fixture(scope="module")
def seed_client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# GET /api/ops/calendar
# ---------------------------------------------------------------------------

class TestOpsCalendar:
    def test_returns_200(self, seed_client):
        resp = seed_client.get("/api/ops/calendar")
        assert resp.status_code == 200

    def test_response_shape(self, seed_client):
        data = seed_client.get("/api/ops/calendar").json()
        assert "events" in data
        assert "total" in data
        assert "as_of" in data

    def test_total_matches_items(self, seed_client):
        data = seed_client.get("/api/ops/calendar").json()
        assert data["total"] == len(data["events"])

    def test_item_fields(self, seed_client):
        data = seed_client.get("/api/ops/calendar").json()
        assert len(data["events"]) > 0
        item = data["events"][0]
        for field in ("id", "title", "event_type", "date", "channel", "owner", "status", "description"):
            assert field in item, f"Missing field: {field}"

    def test_filter_by_month(self, seed_client):
        data = seed_client.get("/api/ops/calendar", params={"month": "2026-05"}).json()
        assert data["total"] > 0
        for item in data["events"]:
            assert item["date"].startswith("2026-05")

    def test_filter_by_channel(self, seed_client):
        data = seed_client.get("/api/ops/calendar", params={"channel": "sem"}).json()
        assert data["total"] > 0
        for item in data["events"]:
            assert item["channel"] in ("sem", "all")

    def test_filter_by_event_type(self, seed_client):
        data = seed_client.get("/api/ops/calendar", params={"event_type": "review"}).json()
        assert data["total"] > 0
        for item in data["events"]:
            assert item["event_type"] == "review"

    def test_filter_no_results(self, seed_client):
        data = seed_client.get("/api/ops/calendar", params={"month": "2020-01"}).json()
        assert data["total"] == 0
        assert data["events"] == []


# ---------------------------------------------------------------------------
# GET /api/ops/capacity
# ---------------------------------------------------------------------------

class TestOpsCapacity:
    def test_returns_200(self, seed_client):
        resp = seed_client.get("/api/ops/capacity")
        assert resp.status_code == 200

    def test_response_shape(self, seed_client):
        data = seed_client.get("/api/ops/capacity").json()
        assert "members" in data, "Missing field: members"
        assert "summary" in data, "Missing field: summary"
        assert "as_of" in data, "Missing field: as_of"
        summary = data["summary"]
        for field in ("total", "total_allocated_hours", "total_used_hours", "avg_utilization_pct"):
            assert field in summary, f"Missing summary field: {field}"

    def test_total_matches_items(self, seed_client):
        data = seed_client.get("/api/ops/capacity").json()
        assert data["summary"]["total"] == len(data["members"])

    def test_item_fields(self, seed_client):
        data = seed_client.get("/api/ops/capacity").json()
        assert len(data["members"]) > 0
        item = data["members"][0]
        for field in ("id", "team", "channel", "period", "allocated_hours",
                      "used_hours", "available_hours", "utilization_pct", "projects"):
            assert field in item, f"Missing field: {field}"

    def test_utilization_pct_range(self, seed_client):
        data = seed_client.get("/api/ops/capacity").json()
        for item in data["members"]:
            assert 0.0 <= item["utilization_pct"] <= 1.0

    def test_filter_by_period(self, seed_client):
        data = seed_client.get("/api/ops/capacity", params={"period": "2026-05"}).json()
        assert data["summary"]["total"] > 0
        for item in data["members"]:
            assert item["period"] == "2026-05"

    def test_filter_by_channel(self, seed_client):
        data = seed_client.get("/api/ops/capacity", params={"channel": "sem"}).json()
        assert data["summary"]["total"] > 0
        for item in data["members"]:
            assert item["channel"] in ("sem", "all")

    def test_filter_by_team(self, seed_client):
        data = seed_client.get("/api/ops/capacity", params={"team": "analytics"}).json()
        assert data["summary"]["total"] > 0
        for item in data["members"]:
            assert "analytics" in item["team"].lower()

    def test_aggregate_hours_are_correct(self, seed_client):
        data = seed_client.get("/api/ops/capacity").json()
        summary = data["summary"]
        assert summary["total_allocated_hours"] == sum(i["allocated_hours"] for i in data["members"])
        assert summary["total_used_hours"] == sum(i["used_hours"] for i in data["members"])

    def test_projects_is_list(self, seed_client):
        data = seed_client.get("/api/ops/capacity").json()
        for item in data["members"]:
            assert isinstance(item["projects"], list)

    def test_filter_no_match_returns_zero(self, seed_client):
        data = seed_client.get("/api/ops/capacity", params={"period": "2099-01"}).json()
        assert data["summary"]["total"] == 0
        assert data["summary"]["total_allocated_hours"] == 0


# ---------------------------------------------------------------------------
# GET /api/ops/approvals
# ---------------------------------------------------------------------------

class TestOpsApprovals:
    def test_returns_200(self, client):
        resp = client.get("/api/ops/approvals")
        assert resp.status_code == 200

    def test_seeds_records_when_empty(self, client):
        data = client.get("/api/ops/approvals").json()
        assert data["count"] > 0
        assert len(data["items"]) > 0

    def test_response_shape(self, client):
        data = client.get("/api/ops/approvals").json()
        assert "items" in data, "Missing field: items"
        assert "count" in data, "Missing field: count"
        assert data["count"] == len(data["items"])
        item = data["items"][0]
        for field in ("id", "title", "approval_type", "priority", "owner",
                      "status", "created_at", "updated_at"):
            assert field in item, f"Missing field: {field}"

    def test_filter_by_status(self, client):
        data = client.get("/api/ops/approvals", params={"status": "pending"}).json()
        assert data["count"] > 0
        for item in data["items"]:
            assert item["status"] == "pending"

    def test_filter_by_priority(self, client):
        data = client.get("/api/ops/approvals", params={"priority": "high"}).json()
        assert data["count"] > 0
        for item in data["items"]:
            assert item["priority"] == "high"

    def test_filter_status_no_results(self, client):
        # No approved records exist yet in fresh DB
        data = client.get("/api/ops/approvals", params={"status": "approved"}).json()
        assert "items" in data
        assert isinstance(data["items"], list)


# ---------------------------------------------------------------------------
# POST /api/ops/approvals/{id}/approve
# ---------------------------------------------------------------------------

class TestApproveApproval:
    def _get_pending_id(self, client) -> str:
        data = client.get("/api/ops/approvals", params={"status": "pending"}).json()
        assert data["count"] > 0, "No pending approvals seeded"
        return data["items"][0]["id"]

    def test_approve_returns_200(self, client):
        aid = self._get_pending_id(client)
        resp = client.post(f"/api/ops/approvals/{aid}/approve")
        assert resp.status_code == 200

    def test_approve_sets_status(self, client):
        aid = self._get_pending_id(client)
        body = client.post(f"/api/ops/approvals/{aid}/approve").json()
        assert body["success"] is True
        # Verify DB update via follow-up GET
        approved = client.get("/api/ops/approvals", params={"status": "approved"}).json()
        assert approved["count"] > 0

    def test_approve_with_comment(self, client):
        aid = self._get_pending_id(client)
        body = client.post(
            f"/api/ops/approvals/{aid}/approve",
            json={"comment": "Approved by CMO"},
        ).json()
        assert body["success"] is True
        assert isinstance(body["message"], str)

    def test_approve_404_unknown_id(self, client):
        fake_id = str(uuid.uuid4())
        resp = client.post(f"/api/ops/approvals/{fake_id}/approve")
        assert resp.status_code == 404

    def test_approve_response_shape(self, client):
        aid = self._get_pending_id(client)
        body = client.post(f"/api/ops/approvals/{aid}/approve").json()
        assert "success" in body
        assert "message" in body
        assert isinstance(body["message"], str)


# ---------------------------------------------------------------------------
# POST /api/ops/approvals/{id}/reject
# ---------------------------------------------------------------------------

class TestRejectApproval:
    def _get_pending_id(self, client) -> str:
        data = client.get("/api/ops/approvals", params={"status": "pending"}).json()
        assert data["count"] > 0, "No pending approvals seeded"
        return data["items"][0]["id"]

    def test_reject_returns_200(self, client):
        aid = self._get_pending_id(client)
        resp = client.post(f"/api/ops/approvals/{aid}/reject")
        assert resp.status_code == 200

    def test_reject_sets_status(self, client):
        aid = self._get_pending_id(client)
        body = client.post(f"/api/ops/approvals/{aid}/reject").json()
        assert body["success"] is True
        # Verify DB update via follow-up GET
        rejected = client.get("/api/ops/approvals", params={"status": "rejected"}).json()
        assert rejected["count"] > 0

    def test_reject_with_comment(self, client):
        aid = self._get_pending_id(client)
        body = client.post(
            f"/api/ops/approvals/{aid}/reject",
            json={"comment": "Budget not available this quarter"},
        ).json()
        assert body["success"] is True
        assert isinstance(body["message"], str)

    def test_reject_404_unknown_id(self, client):
        fake_id = str(uuid.uuid4())
        resp = client.post(f"/api/ops/approvals/{fake_id}/reject")
        assert resp.status_code == 404

    def test_reject_response_shape(self, client):
        aid = self._get_pending_id(client)
        body = client.post(f"/api/ops/approvals/{aid}/reject").json()
        assert "success" in body
        assert "message" in body
        assert body["success"] is True
        assert isinstance(body["message"], str)


# ---------------------------------------------------------------------------
# GET /api/ops/health
# ---------------------------------------------------------------------------

class TestOpsHealth:
    def test_returns_200(self, seed_client):
        resp = seed_client.get("/api/ops/health")
        assert resp.status_code == 200

    def test_response_shape(self, seed_client):
        data = seed_client.get("/api/ops/health").json()
        for field in ("overall_status", "systems", "as_of"):
            assert field in data, f"Missing field: {field}"
        assert isinstance(data["systems"], dict)

    def test_overall_status_is_valid(self, seed_client):
        data = seed_client.get("/api/ops/health").json()
        assert data["overall_status"] in ("healthy", "degraded", "unhealthy")

    def test_systems_keyed_by_name(self, seed_client):
        data = seed_client.get("/api/ops/health").json()
        assert len(data["systems"]) > 0
        # Keys are system names (strings); values have status/last_checked/message
        for name, sys in data["systems"].items():
            assert isinstance(name, str)
            for field in ("status", "last_checked", "message"):
                assert field in sys, f"Missing field '{field}' for system '{name}'"

    def test_component_fields(self, seed_client):
        data = seed_client.get("/api/ops/health").json()
        assert len(data["systems"]) > 0
        sys = next(iter(data["systems"].values()))
        for field in ("status", "last_checked", "message"):
            assert field in sys, f"Missing field: {field}"

    def test_component_status_values(self, seed_client):
        data = seed_client.get("/api/ops/health").json()
        valid = {"healthy", "degraded", "unhealthy"}
        for name, sys in data["systems"].items():
            assert sys["status"] in valid, f"Invalid status for '{name}': {sys['status']}"

    def test_seed_returns_healthy_overall(self, seed_client):
        data = seed_client.get("/api/ops/health").json()
        assert data["overall_status"] == "healthy"


# ---------------------------------------------------------------------------
# GET /api/ops/competitive-feed
# ---------------------------------------------------------------------------

class TestCompetitiveFeed:
    def test_returns_200(self, seed_client):
        resp = seed_client.get("/api/ops/competitive-feed")
        assert resp.status_code == 200

    def test_response_shape(self, seed_client):
        data = seed_client.get("/api/ops/competitive-feed").json()
        assert "items" in data
        assert "total" in data
        assert "as_of" in data

    def test_total_matches_items(self, seed_client):
        data = seed_client.get("/api/ops/competitive-feed").json()
        assert data["total"] == len(data["items"])

    def test_item_fields(self, seed_client):
        data = seed_client.get("/api/ops/competitive-feed").json()
        assert len(data["items"]) > 0
        item = data["items"][0]
        for field in ("id", "competitor", "category", "headline", "summary",
                      "source", "detected_at", "impact", "tags"):
            assert field in item, f"Missing field: {field}"

    def test_filter_by_competitor(self, seed_client):
        data = seed_client.get("/api/ops/competitive-feed", params={"competitor": "Chase"}).json()
        assert data["total"] > 0
        for item in data["items"]:
            assert "chase" in item["competitor"].lower()

    def test_filter_by_category(self, seed_client):
        data = seed_client.get("/api/ops/competitive-feed", params={"category": "product"}).json()
        assert data["total"] > 0
        for item in data["items"]:
            assert item["category"] == "product"

    def test_filter_by_impact(self, seed_client):
        data = seed_client.get("/api/ops/competitive-feed", params={"impact": "high"}).json()
        assert data["total"] > 0
        for item in data["items"]:
            assert item["impact"] == "high"

    def test_limit_param(self, seed_client):
        data = seed_client.get("/api/ops/competitive-feed", params={"limit": 2}).json()
        assert len(data["items"]) <= 2

    def test_tags_is_list(self, seed_client):
        data = seed_client.get("/api/ops/competitive-feed").json()
        for item in data["items"]:
            assert isinstance(item["tags"], list)

    def test_impact_values_are_valid(self, seed_client):
        data = seed_client.get("/api/ops/competitive-feed").json()
        valid = {"high", "medium", "low"}
        for item in data["items"]:
            assert item["impact"] in valid

    def test_filter_no_results(self, seed_client):
        data = seed_client.get("/api/ops/competitive-feed", params={"competitor": "nonexistent_bank_xyz"}).json()
        assert data["total"] == 0
        assert data["items"] == []
