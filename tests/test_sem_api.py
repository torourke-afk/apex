"""Tests for SEM API endpoints (APE-93).

Uses a temp-file DuckDB with raw DDL to mirror the seed schema from APE-88.
Each test class gets one engine; each test cleans its own rows.

Requires src.data.sem_queries (APE-89) to be present.
"""

import tempfile
import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.api import app
from src.data.database import get_session


# ---------------------------------------------------------------------------
# Schema DDL — mirrors seed_sem.py from APE-88
# ---------------------------------------------------------------------------

_SEM_DDL = """
CREATE TABLE IF NOT EXISTS sem_keyword_groups (
    id               VARCHAR PRIMARY KEY,
    keyword_group    VARCHAR NOT NULL,
    match_type       VARCHAR NOT NULL,
    intent_type      VARCHAR NOT NULL,
    market_segment   VARCHAR NOT NULL,
    quality_score    INTEGER NOT NULL,
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sem_daily_performance (
    id               VARCHAR PRIMARY KEY,
    keyword_group_id VARCHAR NOT NULL REFERENCES sem_keyword_groups(id),
    date             DATE NOT NULL,
    impressions      INTEGER NOT NULL DEFAULT 0,
    clicks           INTEGER NOT NULL DEFAULT 0,
    conversions      INTEGER NOT NULL DEFAULT 0,
    spend            DOUBLE NOT NULL DEFAULT 0.0,
    cpc              DOUBLE NOT NULL DEFAULT 0.0,
    ctr              DOUBLE NOT NULL DEFAULT 0.0,
    cvr              DOUBLE NOT NULL DEFAULT 0.0,
    cpl              DOUBLE NOT NULL DEFAULT 0.0,
    impression_share DOUBLE NOT NULL DEFAULT 0.0,
    vbb_margin_signal DOUBLE NOT NULL DEFAULT 0.0,
    quality_score    INTEGER NOT NULL DEFAULT 7,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def tmp_db_url(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("db") / "test_sem.duckdb"
    return f"duckdb:///{db_file}"


@pytest.fixture(scope="module")
def db_engine(tmp_db_url):
    engine = create_engine(tmp_db_url, echo=False)
    with engine.connect() as conn:
        for stmt in _SEM_DDL.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
        conn.commit()
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = Session()
    yield session
    session.execute(text("DELETE FROM sem_daily_performance"))
    session.execute(text("DELETE FROM sem_keyword_groups"))
    session.commit()
    session.close()


@pytest.fixture()
def client(db_session):
    def override():
        yield db_session

    app.dependency_overrides[get_session] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _insert_group(session, *, keyword_group="Test KW", match_type="exact",
                  intent_type="branded", market_segment="established",
                  quality_score=7, is_active=True) -> str:
    gid = str(uuid.uuid4())
    session.execute(
        text(
            "INSERT INTO sem_keyword_groups "
            "(id, keyword_group, match_type, intent_type, market_segment, quality_score, is_active) "
            "VALUES (:id, :kg, :mt, :it, :ms, :qs, :ia)"
        ),
        {"id": gid, "kg": keyword_group, "mt": match_type, "it": intent_type,
         "ms": market_segment, "qs": quality_score, "ia": is_active},
    )
    session.commit()
    return gid


def _insert_perf(session, group_id: str, *, days_ago: int = 1, impressions: int = 1000,
                 clicks: int = 83, conversions: int = 2, spend: float = 150.0,
                 cpc: float = 1.81, ctr: float = 0.083, cvr: float = 0.024,
                 cpl: float = 75.0, impression_share: float = 0.92,
                 vbb_margin_signal: float = 0.5, quality_score: int = 7) -> str:
    pid = str(uuid.uuid4())
    perf_date = date.today() - timedelta(days=days_ago)
    session.execute(
        text(
            "INSERT INTO sem_daily_performance "
            "(id, keyword_group_id, date, impressions, clicks, conversions, spend, "
            "cpc, ctr, cvr, cpl, impression_share, vbb_margin_signal, quality_score) "
            "VALUES (:id, :gid, :dt, :imp, :clk, :cv, :sp, :cpc, :ctr, :cvr, :cpl, :is_, :vbb, :qs)"
        ),
        {"id": pid, "gid": group_id, "dt": perf_date, "imp": impressions,
         "clk": clicks, "cv": conversions, "sp": spend, "cpc": cpc,
         "ctr": ctr, "cvr": cvr, "cpl": cpl, "is_": impression_share,
         "vbb": vbb_margin_signal, "qs": quality_score},
    )
    session.commit()
    return pid


# ---------------------------------------------------------------------------
# GET /api/channels/sem/overview
# ---------------------------------------------------------------------------

class TestSEMOverview:
    def test_empty_db_returns_200(self, client):
        resp = client.get("/api/channels/sem/overview")
        assert resp.status_code == 200

    def test_required_fields_present(self, client):
        resp = client.get("/api/channels/sem/overview")
        assert resp.status_code == 200
        body = resp.json()
        for field in ("avg_cpc", "avg_ctr", "avg_cvr", "avg_cpl",
                      "avg_quality_score", "impression_share_branded",
                      "vbb_margin_signal", "negative_keyword_score",
                      "metrics", "alerts"):
            assert field in body, f"Missing field: {field}"

    def test_metrics_list_has_seven_items(self, client):
        resp = client.get("/api/channels/sem/overview")
        assert resp.status_code == 200
        assert len(resp.json()["metrics"]) == 7

    def test_metric_items_have_benchmark(self, client):
        resp = client.get("/api/channels/sem/overview")
        metrics = resp.json()["metrics"]
        # CPC, CTR, CVR, CPL, QS, IS-Branded all have benchmarks; VBB has none
        with_bench = [m for m in metrics if m["benchmark"] is not None]
        assert len(with_bench) == 6

    def test_high_cpc_triggers_alert(self, client, db_session):
        gid = _insert_group(db_session, intent_type="non_branded")
        _insert_perf(db_session, gid, cpc=6.50, cpl=90.0, ctr=0.08, cvr=0.025,
                     impression_share=0.92, quality_score=8)

        resp = client.get("/api/channels/sem/overview")
        assert resp.status_code == 200
        alerts = resp.json()["alerts"]
        assert any("CPC" in a for a in alerts)

    def test_low_ctr_triggers_alert(self, client, db_session):
        gid = _insert_group(db_session)
        _insert_perf(db_session, gid, ctr=0.04, cpc=3.00, cpl=90.0, cvr=0.025,
                     impression_share=0.92, quality_score=8)

        resp = client.get("/api/channels/sem/overview")
        assert resp.status_code == 200
        alerts = resp.json()["alerts"]
        assert any("CTR" in a for a in alerts)

    def test_low_impression_share_triggers_alert(self, client, db_session):
        gid = _insert_group(db_session, intent_type="branded")
        _insert_perf(db_session, gid, impression_share=0.80, cpc=1.50, ctr=0.10,
                     cvr=0.03, cpl=70.0, quality_score=8)

        resp = client.get("/api/channels/sem/overview")
        assert resp.status_code == 200
        alerts = resp.json()["alerts"]
        assert any("impression share" in a.lower() for a in alerts)

    def test_date_filter_params_accepted(self, client):
        resp = client.get("/api/channels/sem/overview?start_date=2026-01-01&end_date=2026-05-01")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/channels/sem/keywords
# ---------------------------------------------------------------------------

class TestSEMKeywords:
    def test_empty_db_returns_empty_list(self, client):
        resp = client.get("/api/channels/sem/keywords")
        assert resp.status_code == 200
        body = resp.json()
        assert body["groups"] == []
        assert body["total"] == 0

    def test_returns_keyword_groups(self, client, db_session):
        for i in range(3):
            gid = _insert_group(db_session, keyword_group=f"KW Group {i}")
            _insert_perf(db_session, gid)

        resp = client.get("/api/channels/sem/keywords")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert len(body["groups"]) == 3

    def test_group_item_has_required_fields(self, client, db_session):
        gid = _insert_group(db_session)
        _insert_perf(db_session, gid)

        resp = client.get("/api/channels/sem/keywords")
        assert resp.status_code == 200
        item = resp.json()["groups"][0]
        for field in ("keyword_group", "match_type", "intent_type", "market_segment",
                      "quality_score", "spend", "clicks", "impressions", "conversions",
                      "cpc", "ctr", "cvr", "cpl", "impression_share", "is_active"):
            assert field in item, f"Missing field: {field}"

    def test_intent_type_filter(self, client, db_session):
        for intent in ("branded", "non_branded", "pmax"):
            gid = _insert_group(db_session, intent_type=intent, keyword_group=f"{intent} KW")
            _insert_perf(db_session, gid)

        resp = client.get("/api/channels/sem/keywords?intent_type=branded")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["groups"][0]["intent_type"] == "branded"

    def test_match_type_filter(self, client, db_session):
        for mt in ("broad", "exact", "phrase"):
            gid = _insert_group(db_session, match_type=mt, keyword_group=f"{mt} KW")
            _insert_perf(db_session, gid)

        resp = client.get("/api/channels/sem/keywords?match_type=exact")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["groups"][0]["match_type"] == "exact"

    def test_market_segment_filter(self, client, db_session):
        for seg in ("established", "growth", "new"):
            gid = _insert_group(db_session, market_segment=seg, keyword_group=f"{seg} KW")
            _insert_perf(db_session, gid)

        resp = client.get("/api/channels/sem/keywords?market_segment=growth")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_pagination(self, client, db_session):
        for i in range(10):
            gid = _insert_group(db_session, keyword_group=f"Paged KW {i:02d}")
            _insert_perf(db_session, gid)

        resp = client.get("/api/channels/sem/keywords?page=1&page_size=5")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["groups"]) == 5
        assert body["total"] == 10
        assert body["page"] == 1
        assert body["page_size"] == 5

    def test_sort_by_spend(self, client, db_session):
        gid1 = _insert_group(db_session, keyword_group="Low Spend")
        _insert_perf(db_session, gid1, spend=10.0)
        gid2 = _insert_group(db_session, keyword_group="High Spend")
        _insert_perf(db_session, gid2, spend=500.0)

        resp = client.get("/api/channels/sem/keywords?sort=spend")
        assert resp.status_code == 200
        groups = resp.json()["groups"]
        assert len(groups) == 2
        assert groups[0]["spend"] >= groups[1]["spend"]

    def test_invalid_sort_returns_422(self, client):
        resp = client.get("/api/channels/sem/keywords?sort=invalid_column")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/channels/sem/trends
# ---------------------------------------------------------------------------

class TestSEMTrends:
    def test_empty_db_returns_empty_series(self, client):
        resp = client.get("/api/channels/sem/trends")
        assert resp.status_code == 200
        body = resp.json()
        assert body["metric"] == "cpc"
        assert body["period"] == "30d"
        assert isinstance(body["data"], list)

    def test_required_fields_present(self, client):
        resp = client.get("/api/channels/sem/trends?metric=ctr&period=7d")
        assert resp.status_code == 200
        body = resp.json()
        assert "metric" in body
        assert "period" in body
        assert "data" in body
        assert "benchmark" in body

    def test_cpc_has_benchmark(self, client):
        resp = client.get("/api/channels/sem/trends?metric=cpc")
        assert resp.status_code == 200
        assert resp.json()["benchmark"] == pytest.approx(3.46)

    def test_vbb_has_no_benchmark(self, client):
        resp = client.get("/api/channels/sem/trends?metric=vbb_margin_signal")
        assert resp.status_code == 200
        assert resp.json()["benchmark"] is None

    def test_trend_points_have_date_and_value(self, client, db_session):
        gid = _insert_group(db_session)
        for i in range(5):
            _insert_perf(db_session, gid, days_ago=i + 1, cpc=2.50 + i * 0.1)

        resp = client.get("/api/channels/sem/trends?metric=cpc&period=7d")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) > 0
        for pt in data:
            assert "date" in pt
            assert "value" in pt

    def test_period_param_filters_range(self, client, db_session):
        gid = _insert_group(db_session)
        # Insert rows spread over 60 days
        for i in range(60):
            _insert_perf(db_session, gid, days_ago=i + 1)

        resp_7 = client.get("/api/channels/sem/trends?metric=cpc&period=7d")
        resp_30 = client.get("/api/channels/sem/trends?metric=cpc&period=30d")
        assert resp_7.status_code == 200
        assert resp_30.status_code == 200
        assert len(resp_30.json()["data"]) >= len(resp_7.json()["data"])

    def test_invalid_metric_returns_422(self, client):
        resp = client.get("/api/channels/sem/trends?metric=not_a_metric")
        assert resp.status_code == 422

    def test_invalid_period_returns_422(self, client):
        resp = client.get("/api/channels/sem/trends?period=1y")
        assert resp.status_code == 422

    def test_intent_type_filter(self, client, db_session):
        branded_gid = _insert_group(db_session, intent_type="branded")
        nb_gid = _insert_group(db_session, intent_type="non_branded")
        _insert_perf(db_session, branded_gid, cpc=1.50)
        _insert_perf(db_session, nb_gid, cpc=4.00)

        resp = client.get("/api/channels/sem/trends?metric=cpc&period=30d&intent_type=branded")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/channels/sem/match-types
# ---------------------------------------------------------------------------

class TestSEMMatchTypes:
    def test_empty_db_returns_empty_list(self, client):
        resp = client.get("/api/channels/sem/match-types")
        assert resp.status_code == 200
        body = resp.json()
        assert body["match_types"] == []
        assert body["total_spend"] == 0.0

    def test_returns_all_three_match_types(self, client, db_session):
        for mt in ("broad", "exact", "phrase"):
            gid = _insert_group(db_session, match_type=mt, keyword_group=f"{mt} group")
            _insert_perf(db_session, gid, spend=100.0)

        resp = client.get("/api/channels/sem/match-types")
        assert resp.status_code == 200
        body = resp.json()
        match_types = {mt["match_type"] for mt in body["match_types"]}
        assert match_types == {"broad", "exact", "phrase"}

    def test_spend_pct_sums_to_100(self, client, db_session):
        for mt in ("broad", "exact", "phrase"):
            gid = _insert_group(db_session, match_type=mt, keyword_group=f"{mt} pct")
            _insert_perf(db_session, gid, spend=100.0)

        resp = client.get("/api/channels/sem/match-types")
        assert resp.status_code == 200
        total_pct = sum(mt["spend_pct"] for mt in resp.json()["match_types"])
        assert abs(total_pct - 100.0) < 0.01

    def test_match_type_item_has_required_fields(self, client, db_session):
        gid = _insert_group(db_session, match_type="exact")
        _insert_perf(db_session, gid, spend=200.0)

        resp = client.get("/api/channels/sem/match-types")
        assert resp.status_code == 200
        item = resp.json()["match_types"][0]
        for field in ("match_type", "spend", "spend_pct", "clicks", "impressions",
                      "conversions", "cpc", "ctr", "cvr", "cpl"):
            assert field in item, f"Missing field: {field}"

    def test_total_spend_reflects_all_rows(self, client, db_session):
        for mt in ("broad", "exact", "phrase"):
            gid = _insert_group(db_session, match_type=mt, keyword_group=f"{mt} spend")
            _insert_perf(db_session, gid, spend=300.0)

        resp = client.get("/api/channels/sem/match-types")
        assert resp.status_code == 200
        assert resp.json()["total_spend"] == pytest.approx(900.0)

    def test_date_filter_params_accepted(self, client):
        resp = client.get("/api/channels/sem/match-types?start_date=2026-01-01&end_date=2026-05-01")
        assert resp.status_code == 200
