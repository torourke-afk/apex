"""Tests for Ops Command Center data loaders (APE-117 / APE-21c).

Coverage:
  - load_calendar_events: columns, unfiltered, month filter, empty month, invalid status
  - load_approval_queue: columns, unfiltered, status filter, priority ordering, invalid status
  - load_system_health: columns, unfiltered, status severity ordering, invalid status
  - load_competitive_feed: columns, unfiltered, category filter, impact filter,
      unactioned_only, invalid category/impact
  - load_team_capacity: columns, unfiltered, period filter, invalid function
  - approve_item: first call → True, second call (already approved) → False,
      nonexistent id → False
  - reject_item: first call → True, second call → False, reason stored in notes,
      nonexistent id → False

Strategy: monkeypatch `src.data.ops_data.get_connection` to return an in-memory
DuckDB pre-loaded with fixture rows. Each test gets a fresh connection via the
fixture; approve/reject tests share a mutable conn fixture so state carries across
within the test.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import patch

import duckdb
import pandas as pd
import pytest

import src.data.ops_data as loaders

# ---------------------------------------------------------------------------
# DDL — minimal schema matching init_db.py
# ---------------------------------------------------------------------------

_DDL_CALENDAR = """
CREATE TABLE IF NOT EXISTS calendar_events (
    id                   VARCHAR PRIMARY KEY,
    title                VARCHAR NOT NULL,
    event_type           VARCHAR NOT NULL,
    status               VARCHAR NOT NULL DEFAULT 'scheduled',
    start_dt             TIMESTAMP NOT NULL,
    end_dt               TIMESTAMP NOT NULL,
    owner                VARCHAR NOT NULL,
    attendees            VARCHAR,
    description          VARCHAR,
    related_campaign_id  VARCHAR,
    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP
)
"""

_DDL_APPROVAL = """
CREATE TABLE IF NOT EXISTS approval_items (
    id             VARCHAR PRIMARY KEY,
    title          VARCHAR NOT NULL,
    category       VARCHAR NOT NULL,
    status         VARCHAR NOT NULL DEFAULT 'pending',
    priority       VARCHAR NOT NULL DEFAULT 'medium',
    requestor      VARCHAR NOT NULL,
    approver       VARCHAR,
    due_date       TIMESTAMP,
    resolved_at    TIMESTAMP,
    budget_impact  DECIMAL(18, 4),
    notes          VARCHAR,
    artifact_url   VARCHAR,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP
)
"""

_DDL_SYSTEM_HEALTH = """
CREATE TABLE IF NOT EXISTS system_health_checks (
    id                VARCHAR PRIMARY KEY,
    system_name       VARCHAR NOT NULL,
    category          VARCHAR NOT NULL,
    status            VARCHAR NOT NULL,
    checked_at        TIMESTAMP NOT NULL,
    response_time_ms  INTEGER,
    uptime_pct        DECIMAL(7, 4),
    error_message     VARCHAR,
    owner_team        VARCHAR,
    last_incident_at  TIMESTAMP,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP
)
"""

_DDL_INTEL = """
CREATE TABLE IF NOT EXISTS competitive_intel_items (
    id                    VARCHAR PRIMARY KEY,
    competitor_name       VARCHAR NOT NULL,
    category              VARCHAR NOT NULL,
    impact                VARCHAR NOT NULL DEFAULT 'medium',
    headline              VARCHAR NOT NULL,
    detail                VARCHAR,
    source_url            VARCHAR,
    observed_date         DATE NOT NULL,
    product_affected      VARCHAR,
    rate_delta_bps        INTEGER,
    response_recommended  VARCHAR,
    is_actioned           BOOLEAN NOT NULL DEFAULT FALSE,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP
)
"""

_DDL_CAPACITY = """
CREATE TABLE IF NOT EXISTS team_capacity (
    id                    VARCHAR PRIMARY KEY,
    team_name             VARCHAR NOT NULL,
    function              VARCHAR NOT NULL,
    period                VARCHAR(7) NOT NULL,
    headcount_total       INTEGER NOT NULL,
    headcount_fte         INTEGER NOT NULL,
    open_reqs             INTEGER NOT NULL DEFAULT 0,
    utilization_pct       DECIMAL(6, 2) NOT NULL,
    capacity_available_hrs INTEGER,
    notes                 VARCHAR,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP
)
"""


# ---------------------------------------------------------------------------
# Helper: build a fresh in-memory DB with all ops tables and fixtures
# ---------------------------------------------------------------------------

def _make_ops_conn() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(":memory:")
    for ddl in [_DDL_CALENDAR, _DDL_APPROVAL, _DDL_SYSTEM_HEALTH, _DDL_INTEL, _DDL_CAPACITY]:
        conn.execute(ddl)

    # calendar_events — two events in 2026-05, one in 2026-06
    conn.execute("""
        INSERT INTO calendar_events VALUES
        ('ce-001', 'Q2 Campaign Launch', 'campaign_launch', 'scheduled',
         TIMESTAMP '2026-05-10 09:00:00', TIMESTAMP '2026-05-10 10:00:00',
         'Alice', 'Alice, Bob', 'Big launch', NULL, CURRENT_TIMESTAMP, NULL),
        ('ce-002', 'Budget Review', 'budget_review', 'completed',
         TIMESTAMP '2026-05-20 14:00:00', TIMESTAMP '2026-05-20 15:00:00',
         'Bob', NULL, NULL, NULL, CURRENT_TIMESTAMP, NULL),
        ('ce-003', 'June Team Sync', 'team_sync', 'scheduled',
         TIMESTAMP '2026-06-01 10:00:00', TIMESTAMP '2026-06-01 11:00:00',
         'Carol', NULL, NULL, NULL, CURRENT_TIMESTAMP, NULL)
    """)

    # approval_items — one each of pending (high), in_review (urgent), approved (low)
    conn.execute("""
        INSERT INTO approval_items VALUES
        ('ai-001', 'Creative Brief A', 'creative', 'pending', 'high',
         'Dave', NULL, TIMESTAMP '2026-06-01 00:00:00', NULL,
         5000.00, NULL, NULL, CURRENT_TIMESTAMP, NULL),
        ('ai-002', 'Vendor Contract X', 'vendor_contract', 'in_review', 'urgent',
         'Eve', 'Frank', TIMESTAMP '2026-05-15 00:00:00', NULL,
         25000.00, NULL, NULL, CURRENT_TIMESTAMP, NULL),
        ('ai-003', 'Budget Realloc', 'budget_change', 'approved', 'low',
         'Grace', 'Henry', NULL, TIMESTAMP '2026-04-30 00:00:00',
         1000.00, NULL, NULL, CURRENT_TIMESTAMP, NULL)
    """)

    # system_health_checks — down, degraded, healthy
    conn.execute("""
        INSERT INTO system_health_checks VALUES
        ('sh-001', 'CRM Connector', 'integration', 'down',
         CURRENT_TIMESTAMP, NULL, NULL, 'Connection refused', 'Ops',
         TIMESTAMP '2026-05-07 12:00:00', CURRENT_TIMESTAMP, NULL),
        ('sh-002', 'Analytics API', 'analytics', 'degraded',
         CURRENT_TIMESTAMP, 850, 0.9800, NULL, 'Analytics',
         NULL, CURRENT_TIMESTAMP, NULL),
        ('sh-003', 'Campaign DB', 'data_pipeline', 'healthy',
         CURRENT_TIMESTAMP, 45, 0.9999, NULL, 'Data',
         NULL, CURRENT_TIMESTAMP, NULL)
    """)

    # competitive_intel_items — critical + high actioned, medium unactioned
    conn.execute("""
        INSERT INTO competitive_intel_items VALUES
        ('ci-001', 'BankA', 'rate_change', 'critical',
         'BankA cuts HYSA rate 25bps', NULL, NULL,
         DATE '2026-05-01', 'savings', -25, 'Respond within 48h',
         FALSE, CURRENT_TIMESTAMP, NULL),
        ('ci-002', 'BankB', 'product_launch', 'high',
         'BankB launches instant credit line', NULL, NULL,
         DATE '2026-04-28', 'credit', NULL, NULL,
         TRUE, CURRENT_TIMESTAMP, NULL),
        ('ci-003', 'BankA', 'marketing_campaign', 'medium',
         'BankA social blitz', NULL, NULL,
         DATE '2026-04-20', NULL, NULL, NULL,
         FALSE, CURRENT_TIMESTAMP, NULL)
    """)

    # team_capacity — two periods
    conn.execute("""
        INSERT INTO team_capacity VALUES
        ('tc-001', 'Brand Team', 'brand', '2026-05', 8, 7, 1, 90.00, 160, NULL,
         CURRENT_TIMESTAMP, NULL),
        ('tc-002', 'Analytics Team', 'analytics', '2026-05', 5, 5, 0, 75.00, 200, NULL,
         CURRENT_TIMESTAMP, NULL),
        ('tc-003', 'Brand Team', 'brand', '2026-04', 8, 6, 2, 85.00, 180, NULL,
         CURRENT_TIMESTAMP, NULL)
    """)

    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

class _NoCloseConn:
    """Wraps a DuckDB connection so that close() is a no-op.

    approve_item / reject_item call conn.close() after each write. For
    in-memory DuckDB that would destroy all data, breaking subsequent
    reads in the same test. This wrapper keeps the connection open while
    letting the implementation code call close() freely.
    """

    def __init__(self, real: duckdb.DuckDBPyConnection) -> None:
        self._real = real

    def execute(self, *args: Any, **kwargs: Any):
        return self._real.execute(*args, **kwargs)

    def commit(self) -> None:
        self._real.commit()

    def close(self) -> None:
        pass  # intentional no-op


@pytest.fixture()
def conn():
    """Shared in-memory DuckDB for state-mutating tests (approve/reject)."""
    return _make_ops_conn()


def _patch(real_conn: duckdb.DuckDBPyConnection):
    """Context manager: monkeypatch get_connection to return a no-close wrapper."""
    wrapper = _NoCloseConn(real_conn)
    return patch.object(loaders, "get_connection", return_value=wrapper)


# ---------------------------------------------------------------------------
# 1. load_calendar_events
# ---------------------------------------------------------------------------

class TestLoadCalendarEvents:
    EXPECTED_COLS = {
        "id", "title", "event_type", "status", "start_dt",
        "end_dt", "owner", "attendees", "description",
        "related_campaign_id", "created_at",
    }

    def test_unfiltered_returns_all_rows(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_calendar_events()
        assert len(df) == 3
        assert self.EXPECTED_COLS.issubset(df.columns)

    def test_datetime_columns_typed(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_calendar_events()
        for col in ("start_dt", "end_dt", "created_at"):
            assert pd.api.types.is_datetime64_any_dtype(df[col]), f"{col} not datetime"

    def test_month_filter_returns_correct_rows(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_calendar_events(month="2026-05")
        assert len(df) == 2
        for _, row in df.iterrows():
            assert row["start_dt"].strftime("%Y-%m") == "2026-05"

    def test_month_filter_no_match_returns_empty(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_calendar_events(month="2020-01")
        assert len(df) == 0
        assert self.EXPECTED_COLS.issubset(df.columns)

    def test_status_filter(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_calendar_events(status="completed")
        assert len(df) == 1
        assert df.iloc[0]["status"] == "completed"

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError, match="Invalid status"):
            loaders.load_calendar_events(status="bogus")

    def test_invalid_event_type_raises(self):
        with pytest.raises(ValueError, match="Invalid event_type"):
            loaders.load_calendar_events(event_type="not_a_type")

    def test_ordered_by_start_dt_ascending(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_calendar_events()
        dates = df["start_dt"].tolist()
        assert dates == sorted(dates)


# ---------------------------------------------------------------------------
# 2. load_approval_queue
# ---------------------------------------------------------------------------

class TestLoadApprovalQueue:
    EXPECTED_COLS = {
        "id", "title", "category", "status", "priority",
        "requestor", "approver", "due_date", "resolved_at",
        "budget_impact", "notes", "artifact_url", "created_at",
    }

    def test_unfiltered_returns_all_rows(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_approval_queue()
        assert len(df) == 3
        assert self.EXPECTED_COLS.issubset(df.columns)

    def test_status_filter(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_approval_queue(status="pending")
        assert len(df) == 1
        assert df.iloc[0]["status"] == "pending"

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError, match="Invalid status"):
            loaders.load_approval_queue(status="unknown_status")

    def test_invalid_category_raises(self):
        with pytest.raises(ValueError, match="Invalid category"):
            loaders.load_approval_queue(category="not_a_category")

    def test_budget_impact_is_float(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_approval_queue()
        assert df["budget_impact"].dtype == float

    def test_priority_ordering_urgent_first(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_approval_queue()
        # urgent must appear before high
        priorities = df["priority"].tolist()
        assert priorities.index("urgent") < priorities.index("high")

    def test_datetime_columns_typed(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_approval_queue()
        for col in ("due_date", "resolved_at", "created_at"):
            assert pd.api.types.is_datetime64_any_dtype(df[col]), f"{col} not datetime"


# ---------------------------------------------------------------------------
# 3. load_system_health
# ---------------------------------------------------------------------------

class TestLoadSystemHealth:
    EXPECTED_COLS = {
        "id", "system_name", "category", "status", "checked_at",
        "response_time_ms", "uptime_pct", "error_message",
        "owner_team", "last_incident_at", "created_at",
    }

    def test_unfiltered_returns_all_rows(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_system_health()
        assert len(df) == 3
        assert self.EXPECTED_COLS.issubset(df.columns)

    def test_severity_ordering_down_first(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_system_health()
        statuses = df["status"].tolist()
        assert statuses[0] == "down"
        assert statuses[1] == "degraded"
        assert statuses[2] == "healthy"

    def test_status_filter(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_system_health(status="healthy")
        assert len(df) == 1
        assert df.iloc[0]["status"] == "healthy"

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError, match="Invalid status"):
            loaders.load_system_health(status="broken")

    def test_uptime_pct_is_float(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_system_health()
        non_null = df["uptime_pct"].dropna()
        assert non_null.dtype == float

    def test_datetime_columns_typed(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_system_health()
        for col in ("checked_at", "created_at"):
            assert pd.api.types.is_datetime64_any_dtype(df[col]), f"{col} not datetime"


# ---------------------------------------------------------------------------
# 4. load_competitive_feed
# ---------------------------------------------------------------------------

class TestLoadCompetitiveFeed:
    EXPECTED_COLS = {
        "id", "competitor_name", "category", "impact", "headline",
        "detail", "source_url", "observed_date", "product_affected",
        "rate_delta_bps", "response_recommended", "is_actioned", "created_at",
    }

    def test_unfiltered_returns_all_rows(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_competitive_feed()
        assert len(df) == 3
        assert self.EXPECTED_COLS.issubset(df.columns)

    def test_impact_ordering_critical_first(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_competitive_feed()
        assert df.iloc[0]["impact"] == "critical"
        assert df.iloc[1]["impact"] == "high"

    def test_category_filter(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_competitive_feed(category="rate_change")
        assert len(df) == 1
        assert df.iloc[0]["category"] == "rate_change"

    def test_impact_filter(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_competitive_feed(impact="medium")
        assert len(df) == 1
        assert df.iloc[0]["impact"] == "medium"

    def test_unactioned_only(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_competitive_feed(unactioned_only=True)
        assert len(df) == 2
        assert all(~df["is_actioned"])

    def test_competitor_filter(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_competitive_feed(competitor="BankB")
        assert len(df) == 1
        assert df.iloc[0]["competitor_name"] == "BankB"

    def test_invalid_category_raises(self):
        with pytest.raises(ValueError, match="Invalid category"):
            loaders.load_competitive_feed(category="bad_cat")

    def test_invalid_impact_raises(self):
        with pytest.raises(ValueError, match="Invalid impact"):
            loaders.load_competitive_feed(impact="extreme")

    def test_observed_date_is_date_type(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_competitive_feed()
        import datetime
        for val in df["observed_date"].dropna():
            assert isinstance(val, datetime.date)


# ---------------------------------------------------------------------------
# 5. load_team_capacity
# ---------------------------------------------------------------------------

class TestLoadTeamCapacity:
    EXPECTED_COLS = {
        "id", "team_name", "function", "period", "headcount_total",
        "headcount_fte", "open_reqs", "utilization_pct",
        "capacity_available_hrs", "notes", "created_at",
    }

    def test_unfiltered_returns_all_rows(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_team_capacity()
        assert len(df) == 3
        assert self.EXPECTED_COLS.issubset(df.columns)

    def test_period_filter(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_team_capacity(period="2026-05")
        assert len(df) == 2
        assert all(df["period"] == "2026-05")

    def test_function_filter(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_team_capacity(function="analytics")
        assert len(df) == 1
        assert df.iloc[0]["function"] == "analytics"

    def test_invalid_function_raises(self):
        with pytest.raises(ValueError, match="Invalid function"):
            loaders.load_team_capacity(function="unknown_fn")

    def test_utilization_pct_is_float(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_team_capacity()
        assert df["utilization_pct"].dtype == float

    def test_ordered_period_desc_then_utilization_desc(self):
        with patch("src.data.ops_data.get_connection", _make_ops_conn):
            df = loaders.load_team_capacity()
        # Most recent period first
        assert df.iloc[0]["period"] >= df.iloc[-1]["period"]


# ---------------------------------------------------------------------------
# 6 & 7. approve_item / reject_item — stateful tests on shared conn
# ---------------------------------------------------------------------------

class TestApproveItem:
    def test_approve_pending_returns_true(self, conn):
        with _patch(conn):
            result = loaders.approve_item("ai-001")
        assert result is True

    def test_approve_sets_status_approved(self, conn):
        with _patch(conn):
            loaders.approve_item("ai-001")
        row = conn.execute("SELECT status FROM approval_items WHERE id = 'ai-001'").fetchone()
        assert row[0] == "approved"

    def test_approve_already_approved_returns_false(self, conn):
        with _patch(conn):
            loaders.approve_item("ai-001")  # first call
            result = loaders.approve_item("ai-001")  # second call — already terminal
        assert result is False

    def test_approve_nonexistent_id_returns_false(self, conn):
        with _patch(conn):
            result = loaders.approve_item(str(uuid.uuid4()))
        assert result is False

    def test_approve_already_approved_fixture_returns_false(self, conn):
        # ai-003 is already in 'approved' state in the fixture
        with _patch(conn):
            result = loaders.approve_item("ai-003")
        assert result is False

    def test_approve_in_review_item_returns_true(self, conn):
        # ai-002 is in_review — should be approvable
        with _patch(conn):
            result = loaders.approve_item("ai-002")
        assert result is True

    def test_approve_records_approver(self, conn):
        with _patch(conn):
            loaders.approve_item("ai-001", approver="QA Bot")
        row = conn.execute("SELECT approver FROM approval_items WHERE id = 'ai-001'").fetchone()
        assert row[0] == "QA Bot"


class TestRejectItem:
    def test_reject_pending_returns_true(self, conn):
        with _patch(conn):
            result = loaders.reject_item("ai-001")
        assert result is True

    def test_reject_sets_status_rejected(self, conn):
        with _patch(conn):
            loaders.reject_item("ai-001", reason="Not in budget")
        row = conn.execute("SELECT status, notes FROM approval_items WHERE id = 'ai-001'").fetchone()
        assert row[0] == "rejected"
        assert row[1] == "Not in budget"

    def test_reject_already_rejected_returns_false(self, conn):
        with _patch(conn):
            loaders.reject_item("ai-001")
            result = loaders.reject_item("ai-001")
        assert result is False

    def test_reject_already_approved_returns_false(self, conn):
        # ai-003 is already approved — reject must be a no-op
        with _patch(conn):
            result = loaders.reject_item("ai-003", reason="Too late")
        assert result is False

    def test_reject_nonexistent_id_returns_false(self, conn):
        with _patch(conn):
            result = loaders.reject_item(str(uuid.uuid4()))
        assert result is False

    def test_reject_in_review_item_returns_true(self, conn):
        with _patch(conn):
            result = loaders.reject_item("ai-002", reason="Vendor terms unacceptable")
        assert result is True

    def test_approve_then_reject_is_idempotent(self, conn):
        """Once approved, reject must return False (not corrupt the record)."""
        with _patch(conn):
            assert loaders.approve_item("ai-001") is True
            assert loaders.reject_item("ai-001") is False
        row = conn.execute("SELECT status FROM approval_items WHERE id = 'ai-001'").fetchone()
        assert row[0] == "approved"  # status unchanged after failed reject
