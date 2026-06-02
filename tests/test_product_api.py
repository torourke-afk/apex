"""Tests for Product & Experience API endpoints (APE-113).

All three endpoints are backed by seed data and require no database fixtures,
so the test client is constructed once per module against the real app.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# GET /api/product/pipeline
# ---------------------------------------------------------------------------

class TestProductPipeline:
    def test_pipeline_returns_200(self, client: TestClient):
        resp = client.get("/api/product/pipeline")
        assert resp.status_code == 200

    def test_pipeline_response_shape(self, client: TestClient):
        data = client.get("/api/product/pipeline").json()
        assert "items" in data
        assert "total" in data
        assert "stage_counts" in data
        assert "as_of" in data

    def test_pipeline_total_matches_items(self, client: TestClient):
        data = client.get("/api/product/pipeline").json()
        assert data["total"] == len(data["items"])

    def test_pipeline_item_fields(self, client: TestClient):
        data = client.get("/api/product/pipeline").json()
        assert len(data["items"]) > 0
        item = data["items"][0]
        for field in ("id", "name", "product_line", "stage", "owner", "target_date", "priority", "confidence_score", "description"):
            assert field in item, f"Missing field: {field}"

    def test_pipeline_filter_by_stage(self, client: TestClient):
        data = client.get("/api/product/pipeline", params={"stage": "testing"}).json()
        assert data["total"] > 0
        for item in data["items"]:
            assert item["stage"] == "testing"

    def test_pipeline_filter_by_product_line(self, client: TestClient):
        data = client.get("/api/product/pipeline", params={"product_line": "checking"}).json()
        assert data["total"] > 0
        for item in data["items"]:
            assert item["product_line"] == "checking"

    def test_pipeline_filter_no_results(self, client: TestClient):
        data = client.get("/api/product/pipeline", params={"stage": "ideation", "product_line": "cards"}).json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_pipeline_stage_counts_all_stages_present(self, client: TestClient):
        data = client.get("/api/product/pipeline").json()
        for stage in ("ideation", "discovery", "development", "testing", "launched"):
            assert stage in data["stage_counts"], f"Missing stage in stage_counts: {stage}"

    def test_pipeline_confidence_score_range(self, client: TestClient):
        data = client.get("/api/product/pipeline").json()
        for item in data["items"]:
            assert 0.0 <= item["confidence_score"] <= 1.0


# ---------------------------------------------------------------------------
# GET /api/product/roadmap
# ---------------------------------------------------------------------------

class TestProductRoadmap:
    def test_roadmap_returns_200(self, client: TestClient):
        resp = client.get("/api/product/roadmap")
        assert resp.status_code == 200

    def test_roadmap_response_shape(self, client: TestClient):
        data = client.get("/api/product/roadmap").json()
        assert "items" in data
        assert "total" in data
        assert "by_quarter" in data
        assert "total_effort_weeks" in data
        assert "as_of" in data

    def test_roadmap_total_matches_items(self, client: TestClient):
        data = client.get("/api/product/roadmap").json()
        assert data["total"] == len(data["items"])

    def test_roadmap_item_fields(self, client: TestClient):
        data = client.get("/api/product/roadmap").json()
        assert len(data["items"]) > 0
        item = data["items"][0]
        for field in ("id", "initiative", "product_line", "quarter", "status", "priority", "theme", "owner", "dependencies", "kpi_target", "effort_weeks"):
            assert field in item, f"Missing field: {field}"

    def test_roadmap_filter_by_quarter(self, client: TestClient):
        data = client.get("/api/product/roadmap", params={"quarter": "Q2-2026"}).json()
        assert data["total"] > 0
        for item in data["items"]:
            assert item["quarter"] == "Q2-2026"

    def test_roadmap_filter_by_theme(self, client: TestClient):
        data = client.get("/api/product/roadmap", params={"theme": "acquisition"}).json()
        assert data["total"] > 0
        for item in data["items"]:
            assert item["theme"] == "acquisition"

    def test_roadmap_filter_by_product_line(self, client: TestClient):
        data = client.get("/api/product/roadmap", params={"product_line": "digital"}).json()
        assert data["total"] > 0
        for item in data["items"]:
            assert item["product_line"] == "digital"

    def test_roadmap_total_effort_is_sum(self, client: TestClient):
        data = client.get("/api/product/roadmap").json()
        computed = sum(i["effort_weeks"] for i in data["items"])
        assert data["total_effort_weeks"] == computed

    def test_roadmap_by_quarter_keys_match_items(self, client: TestClient):
        data = client.get("/api/product/roadmap").json()
        for item in data["items"]:
            assert item["quarter"] in data["by_quarter"]

    def test_roadmap_dependencies_is_list(self, client: TestClient):
        data = client.get("/api/product/roadmap").json()
        for item in data["items"]:
            assert isinstance(item["dependencies"], list)


# ---------------------------------------------------------------------------
# GET /api/product/testing-velocity
# ---------------------------------------------------------------------------

class TestTestingVelocity:
    def test_velocity_returns_200(self, client: TestClient):
        resp = client.get("/api/product/testing-velocity")
        assert resp.status_code == 200

    def test_velocity_response_shape(self, client: TestClient):
        data = client.get("/api/product/testing-velocity").json()
        for field in (
            "period", "tests_run", "tests_won", "tests_inconclusive", "tests_lost",
            "win_rate", "avg_lift_pct", "avg_duration_days",
            "baseline_tests_run", "baseline_win_rate", "baseline_avg_lift_pct",
            "tests_run_delta", "tests_run_delta_pct", "win_rate_delta", "lift_delta",
            "as_of",
        ):
            assert field in data, f"Missing field: {field}"

    def test_velocity_default_period_is_30d(self, client: TestClient):
        data = client.get("/api/product/testing-velocity").json()
        assert data["period"] == "30d"

    def test_velocity_period_60d(self, client: TestClient):
        data = client.get("/api/product/testing-velocity", params={"period": "60d"}).json()
        assert data["period"] == "60d"
        assert data["tests_run"] > 0

    def test_velocity_period_90d(self, client: TestClient):
        data = client.get("/api/product/testing-velocity", params={"period": "90d"}).json()
        assert data["period"] == "90d"
        assert data["tests_run"] > 0

    def test_velocity_win_rate_is_fraction(self, client: TestClient):
        data = client.get("/api/product/testing-velocity").json()
        assert 0.0 <= data["win_rate"] <= 1.0

    def test_velocity_tests_sum_correctly(self, client: TestClient):
        data = client.get("/api/product/testing-velocity").json()
        total = data["tests_won"] + data["tests_inconclusive"] + data["tests_lost"]
        assert total == data["tests_run"]

    def test_velocity_baseline_comparison_fields_numeric(self, client: TestClient):
        data = client.get("/api/product/testing-velocity").json()
        assert isinstance(data["tests_run_delta"], int)
        assert isinstance(data["win_rate_delta"], float)
        assert isinstance(data["lift_delta"], float)

    def test_velocity_90d_has_more_tests_than_30d(self, client: TestClient):
        d30 = client.get("/api/product/testing-velocity", params={"period": "30d"}).json()
        d90 = client.get("/api/product/testing-velocity", params={"period": "90d"}).json()
        assert d90["tests_run"] > d30["tests_run"]

    def test_velocity_invalid_period_returns_422(self, client: TestClient):
        resp = client.get("/api/product/testing-velocity", params={"period": "7d"})
        assert resp.status_code == 422
