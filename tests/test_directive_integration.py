"""End-to-end integration tests for the Kamino directive bus (APE-137 / APE-25e).

Six scenarios:
  1. Full lifecycle      — submit → approved → in_progress → completed
  2. Validation rejection — invalid DirectivePayload (Pydantic) + Kamino 400
  3. Cancel flow         — KaminoClient.cancel_job + REST PATCH /cancel
  4. Kamino failure      — 5xx retry exhaustion, 404, 401
  5. List / filter       — REST GET /api/directives with status/type/owner/limit
  6. Redis degradation   — publish returns False when Redis is down; API still 201

Mocking strategy:
  - Kamino HTTP calls: custom _KaminoMockTransport (httpx.AsyncBaseTransport)
  - Redis pub/sub:     fakeredis.FakeRedis patched into src.kamino.events._get_sync_redis
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import fakeredis
import httpx
import pytest
import pytest_asyncio  # noqa: F401  — ensures asyncio mode plugin is registered
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api import app
from src.data.database import get_session
from src.data.orm import Base, Directive as DirectiveORM
from src.kamino.client import (
    KaminoAuthError,
    KaminoClient,
    KaminoHTTPError,
    KaminoNotFoundError,
    KaminoRetryExhaustedError,
)
from src.kamino.events import (
    DIRECTIVE_EVENT_CHANNEL,
    DirectiveEvent,
    publish_directive_event,
)
from src.kamino.models import DirectivePayload, DirectiveStatus, DirectiveType


# ---------------------------------------------------------------------------
# Mock Kamino HTTP transport
# ---------------------------------------------------------------------------


class _KaminoMockTransport(httpx.AsyncBaseTransport):
    """Canned-response transport for testing KaminoClient without a real server.

    Responses are consumed from *response_queue* in order.  Once the queue is
    exhausted the last entry is repeated for every subsequent request.

    Each queue entry is ``(status_code: int, body: dict)``.
    """

    def __init__(self, response_queue: list[tuple[int, dict]]) -> None:
        self._queue = list(response_queue)
        self._pos = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:  # type: ignore[override]
        if self._pos < len(self._queue):
            status, body = self._queue[self._pos]
            self._pos += 1
        else:
            status, body = self._queue[-1]
        return httpx.Response(
            status_code=status,
            json=body,
            request=request,
        )


# ---------------------------------------------------------------------------
# Shared directive payloads / helpers
# ---------------------------------------------------------------------------

_VALID_KAMINO_PAYLOAD = DirectivePayload(
    type=DirectiveType.budget_reallocation,
    parameters={"from_channel": "sem", "to_channel": "display", "amount": 5000},
    description="Shift Q3 budget from SEM to display",
    source_module="spend_allocation",
)

_REST_SUBMIT_PAYLOAD = {
    "title": "Increase SEM budget Q3",
    "directive_type": "tactical",
    "priority": "high",
    "owner": "integration-tester",
    "status": "pending",
}


def _directive_orm(
    title: str = "Integration Test Directive",
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


# ---------------------------------------------------------------------------
# DB + REST client fixtures (function-scoped for isolation)
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_db_url(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("db") / "test_integration.duckdb"
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
    def _override():
        yield db_session

    app.dependency_overrides[get_session] = _override
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.pop(get_session, None)


# ---------------------------------------------------------------------------
# Scenario 1 — Full lifecycle: submit → approved → in_progress → completed
# ---------------------------------------------------------------------------


class TestFullLifecycle:
    @pytest.mark.asyncio
    async def test_submit_approve_execute_complete(self):
        """KaminoClient walks a directive through all four status transitions."""
        transport = _KaminoMockTransport([
            (200, {"job_id": "job-lifecycle", "status": "pending", "message": "queued"}),
            (200, {"job_id": "job-lifecycle", "status": "approved", "started_at": None}),
            (200, {
                "job_id": "job-lifecycle",
                "status": "in_progress",
                "started_at": "2026-05-08T10:00:00",
            }),
            (200, {
                "job_id": "job-lifecycle",
                "status": "completed",
                "started_at": "2026-05-08T10:00:00",
                "completed_at": "2026-05-08T10:05:00",
            }),
        ])

        async with KaminoClient(_transport=transport, max_retries=0) as client:
            submit = await client.submit_directive(_VALID_KAMINO_PAYLOAD)
            assert submit.job_id == "job-lifecycle"
            assert submit.status == DirectiveStatus.pending

            approved = await client.check_job_status("job-lifecycle")
            assert approved.status == DirectiveStatus.approved

            in_progress = await client.check_job_status("job-lifecycle")
            assert in_progress.status == DirectiveStatus.in_progress
            assert in_progress.started_at is not None

            completed = await client.check_job_status("job-lifecycle")
            assert completed.status == DirectiveStatus.completed
            assert completed.completed_at is not None

    def test_rest_submit_and_poll_lifecycle(self, client, db_session):
        """POST directive via REST then poll GET through all status transitions."""
        # 1. Submit via REST
        resp = client.post("/api/directives", json=_REST_SUBMIT_PAYLOAD)
        assert resp.status_code == 201
        body = resp.json()
        directive_id = body["id"]
        assert body["status"] == "pending"

        # 2. Verify initial state via GET
        resp = client.get(f"/api/directives/{directive_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"

        # 3. Simulate Kamino advancing status: pending → approved → in_progress → completed
        for new_status in ("approved", "in_progress", "completed"):
            row = db_session.query(DirectiveORM).filter(
                DirectiveORM.id == uuid.UUID(directive_id)
            ).first()
            row.status = new_status
            row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db_session.commit()

            # Verify via /status shortcut
            resp = client.get(f"/api/directives/{directive_id}/status")
            assert resp.status_code == 200
            assert resp.json()["status"] == new_status

            # Verify via full detail endpoint
            resp = client.get(f"/api/directives/{directive_id}")
            assert resp.status_code == 200
            assert resp.json()["status"] == new_status

    @pytest.mark.asyncio
    async def test_submit_payload_serialised_correctly(self):
        """Ensures DirectivePayload JSON is sent in the POST body."""
        received_bodies: list[bytes] = []

        class _CapturingTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request: httpx.Request):  # type: ignore[override]
                received_bodies.append(request.content)
                return httpx.Response(
                    200,
                    json={"job_id": "job-capture", "status": "pending"},
                    request=request,
                )

        async with KaminoClient(_transport=_CapturingTransport(), max_retries=0) as c:
            await c.submit_directive(_VALID_KAMINO_PAYLOAD)

        assert len(received_bodies) == 1
        body = json.loads(received_bodies[0])
        assert body["type"] == "budget_reallocation"
        assert body["source_module"] == "spend_allocation"
        assert body["parameters"]["amount"] == 5000


# ---------------------------------------------------------------------------
# Scenario 2 — Validation rejection
# ---------------------------------------------------------------------------


class TestValidationRejection:
    def test_empty_parameters_rejected_by_pydantic(self):
        with pytest.raises(Exception, match="parameters must be a non-empty dict"):
            DirectivePayload(
                type=DirectiveType.budget_reallocation,
                parameters={},
                description="No params",
                source_module="spend_allocation",
            )

    def test_invalid_source_module_rejected_by_pydantic(self):
        with pytest.raises(Exception, match="source_module must be one of"):
            DirectivePayload(
                type=DirectiveType.budget_reallocation,
                parameters={"amount": 100},
                description="Bad module",
                source_module="completely_unknown",
            )

    @pytest.mark.asyncio
    async def test_kamino_400_raises_http_error(self):
        """When Kamino returns 400 the client raises KaminoHTTPError."""
        transport = _KaminoMockTransport([
            (400, {"detail": "Directive payload failed schema validation"}),
        ])
        async with KaminoClient(_transport=transport, max_retries=0) as client:
            with pytest.raises(KaminoHTTPError) as exc_info:
                await client.submit_directive(_VALID_KAMINO_PAYLOAD)
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_kamino_422_raises_http_error(self):
        transport = _KaminoMockTransport([
            (422, {"detail": "Unprocessable entity"}),
        ])
        async with KaminoClient(_transport=transport, max_retries=0) as client:
            with pytest.raises(KaminoHTTPError) as exc_info:
                await client.submit_directive(_VALID_KAMINO_PAYLOAD)
            assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# Scenario 3 — Cancel flow
# ---------------------------------------------------------------------------


class TestCancelFlow:
    @pytest.mark.asyncio
    async def test_cancel_job_via_kamino_client(self):
        """submit_directive → cancel_job transitions status to cancelled."""
        transport = _KaminoMockTransport([
            (200, {"job_id": "job-cancel", "status": "pending", "message": "queued"}),
            (200, {"job_id": "job-cancel", "status": "cancelled", "message": "Job cancelled by user"}),
        ])
        async with KaminoClient(_transport=transport, max_retries=0) as client:
            submit = await client.submit_directive(_VALID_KAMINO_PAYLOAD)
            assert submit.job_id == "job-cancel"

            cancel = await client.cancel_job("job-cancel")
            assert cancel.status == DirectiveStatus.cancelled
            assert cancel.job_id == "job-cancel"

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_job_raises_not_found(self):
        transport = _KaminoMockTransport([
            (404, {"detail": "Job job-ghost not found"}),
        ])
        async with KaminoClient(_transport=transport, max_retries=0) as client:
            with pytest.raises(KaminoNotFoundError):
                await client.cancel_job("job-ghost")

    def test_rest_cancel_transitions_directive_to_cancelled(self, client, db_session):
        """PATCH /api/directives/{id}/cancel returns status='cancelled'."""
        row = _directive_orm(status="pending")
        db_session.add(row)
        db_session.commit()

        resp = client.patch(f"/api/directives/{row.id}/cancel")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_rest_cancel_is_idempotent(self, client, db_session):
        row = _directive_orm(status="cancelled")
        db_session.add(row)
        db_session.commit()

        resp = client.patch(f"/api/directives/{row.id}/cancel")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_rest_cancel_persists_to_db(self, client, db_session):
        row = _directive_orm(status="pending")
        db_session.add(row)
        db_session.commit()

        client.patch(f"/api/directives/{row.id}/cancel")
        db_session.expire(row)
        db_session.refresh(row)
        assert row.status == "cancelled"

    def test_rest_cancel_after_complete_returns_409(self, client, db_session):
        """Cancelling a completed directive must return 409 Conflict."""
        row = _directive_orm(status="completed")
        db_session.add(row)
        db_session.commit()

        resp = client.patch(f"/api/directives/{row.id}/cancel")
        assert resp.status_code == 409
        assert "completed" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Scenario 4 — Kamino failure handling
# ---------------------------------------------------------------------------


class TestKaminoFailureHandling:
    @pytest.mark.asyncio
    async def test_500_retries_then_exhausted(self):
        """Persistent 500 responses exhaust all retries and raise KaminoRetryExhaustedError."""
        transport = _KaminoMockTransport([
            (500, {"detail": "Internal server error"}),
        ])
        async with KaminoClient(_transport=transport, max_retries=2, backoff_base=0.0) as client:
            with pytest.raises(KaminoRetryExhaustedError):
                await client.submit_directive(_VALID_KAMINO_PAYLOAD)

    @pytest.mark.asyncio
    async def test_503_retries_then_exhausted(self):
        transport = _KaminoMockTransport([
            (503, {"detail": "Service unavailable"}),
        ])
        async with KaminoClient(_transport=transport, max_retries=1, backoff_base=0.0) as client:
            with pytest.raises(KaminoRetryExhaustedError):
                await client.submit_directive(_VALID_KAMINO_PAYLOAD)

    @pytest.mark.asyncio
    async def test_transient_500_then_success(self):
        """A single 500 followed by success should succeed (one retry allowed)."""
        transport = _KaminoMockTransport([
            (500, {"detail": "Transient error"}),
            (200, {"job_id": "job-recovered", "status": "pending"}),
        ])
        async with KaminoClient(_transport=transport, max_retries=1, backoff_base=0.0) as client:
            resp = await client.submit_directive(_VALID_KAMINO_PAYLOAD)
        assert resp.job_id == "job-recovered"
        assert resp.status == DirectiveStatus.pending

    @pytest.mark.asyncio
    async def test_404_raises_not_found_immediately(self):
        """404 is not retried — raises KaminoNotFoundError on the first attempt."""
        transport = _KaminoMockTransport([
            (404, {"detail": "Job not found"}),
        ])
        async with KaminoClient(_transport=transport, max_retries=3, backoff_base=0.0) as client:
            with pytest.raises(KaminoNotFoundError):
                await client.check_job_status("job-missing")
        # Verify only one request was made (no retries)
        assert transport._pos == 1

    @pytest.mark.asyncio
    async def test_401_raises_auth_error(self):
        transport = _KaminoMockTransport([
            (401, {"detail": "Unauthorized"}),
        ])
        async with KaminoClient(_transport=transport, max_retries=0) as client:
            with pytest.raises(KaminoAuthError) as exc_info:
                await client.submit_directive(_VALID_KAMINO_PAYLOAD)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_403_raises_auth_error(self):
        transport = _KaminoMockTransport([
            (403, {"detail": "Forbidden"}),
        ])
        async with KaminoClient(_transport=transport, max_retries=0) as client:
            with pytest.raises(KaminoAuthError) as exc_info:
                await client.submit_directive(_VALID_KAMINO_PAYLOAD)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_job_status_failed(self):
        """A completed-with-failure Kamino job surfaces the failure_reason."""
        transport = _KaminoMockTransport([
            (200, {
                "job_id": "job-fail",
                "status": "failed",
                "failure_reason": "Budget cap exceeded",
                "started_at": "2026-05-08T09:00:00",
            }),
        ])
        async with KaminoClient(_transport=transport, max_retries=0) as client:
            status = await client.check_job_status("job-fail")
        assert status.status == DirectiveStatus.failed
        assert status.failure_reason == "Budget cap exceeded"


# ---------------------------------------------------------------------------
# Scenario 5 — List / filter
# ---------------------------------------------------------------------------


class TestListFilter:
    def test_empty_list_when_no_directives(self, client):
        resp = client.get("/api/directives")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_filter_by_status(self, client, db_session):
        db_session.add_all([
            _directive_orm(status="pending"),
            _directive_orm(status="cancelled"),
            _directive_orm(status="completed"),
        ])
        db_session.commit()

        resp = client.get("/api/directives?status=pending")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) >= 1
        assert all(i["status"] == "pending" for i in items)

    def test_filter_by_directive_type(self, client, db_session):
        db_session.add_all([
            _directive_orm(directive_type="strategic"),
            _directive_orm(directive_type="tactical"),
            _directive_orm(directive_type="operational"),
        ])
        db_session.commit()

        resp = client.get("/api/directives?directive_type=tactical")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) >= 1
        assert all(i["directive_type"] == "tactical" for i in items)

    def test_filter_by_owner(self, client, db_session):
        db_session.add_all([
            _directive_orm(owner="alice"),
            _directive_orm(owner="bob"),
            _directive_orm(owner="charlie"),
        ])
        db_session.commit()

        resp = client.get("/api/directives?owner=alice")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) >= 1
        assert all(i["owner"] == "alice" for i in items)

    def test_limit_param(self, client, db_session):
        for i in range(8):
            db_session.add(_directive_orm(title=f"Directive {i}"))
        db_session.commit()

        resp = client.get("/api/directives?limit=3")
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_combined_status_and_owner_filter(self, client, db_session):
        db_session.add_all([
            _directive_orm(owner="diana", status="pending"),
            _directive_orm(owner="diana", status="cancelled"),
            _directive_orm(owner="evan", status="pending"),
        ])
        db_session.commit()

        resp = client.get("/api/directives?owner=diana&status=active")
        assert resp.status_code == 200
        items = resp.json()
        assert all(i["owner"] == "diana" and i["status"] == "pending" for i in items)

    def test_response_shape(self, client, db_session):
        db_session.add(_directive_orm())
        db_session.commit()

        resp = client.get("/api/directives")
        assert resp.status_code == 200
        item = resp.json()[0]
        for field in (
            "id", "title", "directive_type", "priority", "owner",
            "due_date", "status", "notes", "created_at", "updated_at",
        ):
            assert field in item, f"Missing field: {field}"

    def test_ordered_by_created_at_desc(self, client, db_session):
        from datetime import timedelta

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        older = _directive_orm(title="Older", created_at=now - timedelta(hours=3), updated_at=now)
        newer = _directive_orm(title="Newer", created_at=now, updated_at=now)
        db_session.add_all([older, newer])
        db_session.commit()

        resp = client.get("/api/directives")
        titles = [i["title"] for i in resp.json()]
        idx_newer = titles.index("Newer")
        idx_older = titles.index("Older")
        assert idx_newer < idx_older


# ---------------------------------------------------------------------------
# Scenario 6 — Redis degradation
# ---------------------------------------------------------------------------


class TestRedisDegradation:
    def test_publish_returns_false_when_redis_unavailable(self):
        """When _get_sync_redis returns None, publish_directive_event is a no-op."""
        event = DirectiveEvent(
            directive_id=uuid.uuid4(),
            event_type="created",
            status="pending",
            occurred_at=datetime.now(timezone.utc),
            title="Degradation test",
            owner="tester",
        )
        with patch("src.kamino.events._get_sync_redis", return_value=None):
            result = publish_directive_event(event)
        assert result is False

    def test_publish_succeeds_with_fakeredis(self):
        """With fakeredis in place, publish_directive_event returns True."""
        fake_r = fakeredis.FakeRedis(decode_responses=True)
        pubsub = fake_r.pubsub()
        pubsub.subscribe(DIRECTIVE_EVENT_CHANNEL)
        # Drain the subscribe confirmation message
        pubsub.get_message()

        event = DirectiveEvent(
            directive_id=uuid.uuid4(),
            event_type="created",
            status="pending",
            occurred_at=datetime.now(timezone.utc),
            title="Redis test directive",
            owner="tester",
        )
        with patch("src.kamino.events._get_sync_redis", return_value=fake_r):
            result = publish_directive_event(event)

        assert result is True
        msg = pubsub.get_message(timeout=0.1)
        assert msg is not None
        assert msg["type"] == "message"
        assert msg["channel"] == DIRECTIVE_EVENT_CHANNEL
        data = json.loads(msg["data"])
        assert data["event_type"] == "created"
        assert data["status"] == "pending"

    def test_all_lifecycle_events_arrive_in_order(self):
        """All 4 lifecycle events arrive on the channel in submission order."""
        fake_r = fakeredis.FakeRedis(decode_responses=True)
        pubsub = fake_r.pubsub()
        pubsub.subscribe(DIRECTIVE_EVENT_CHANNEL)
        pubsub.get_message()  # drain subscribe confirmation

        did = uuid.uuid4()
        lifecycle = [
            ("created", "pending"),
            ("status_changed", "approved"),
            ("status_changed", "in_progress"),
            ("status_changed", "completed"),
        ]

        with patch("src.kamino.events._get_sync_redis", return_value=fake_r):
            for event_type, status in lifecycle:
                result = publish_directive_event(
                    DirectiveEvent(
                        directive_id=did,
                        event_type=event_type,
                        status=status,
                        occurred_at=datetime.now(timezone.utc),
                        title="Lifecycle Redis test",
                        owner="tester",
                    )
                )
                assert result is True

        received = []
        for _ in range(4):
            msg = pubsub.get_message(timeout=0.1)
            assert msg is not None and msg["type"] == "message"
            received.append(json.loads(msg["data"]))

        assert [r["event_type"] for r in received] == [et for et, _ in lifecycle]
        assert [r["status"] for r in received] == [s for _, s in lifecycle]
        assert all(r["directive_id"] == str(did) for r in received)

    def test_rest_api_returns_201_when_redis_down(self, client):
        """POST /api/directives must succeed even when Redis is unavailable."""
        with patch("src.kamino.events._get_sync_redis", return_value=None):
            resp = client.post("/api/directives", json=_REST_SUBMIT_PAYLOAD)
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == _REST_SUBMIT_PAYLOAD["title"]

    def test_cancel_via_rest_succeeds_when_redis_down(self, client, db_session):
        """PATCH /cancel must succeed even when Redis is unavailable."""
        row = _directive_orm(status="pending")
        db_session.add(row)
        db_session.commit()

        with patch("src.kamino.events._get_sync_redis", return_value=None):
            resp = client.patch(f"/api/directives/{row.id}/cancel")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_subscriber_yields_nothing_when_redis_down(self):
        """directive_event_subscriber degrades gracefully when Redis is unreachable."""
        import redis.asyncio as aioredis

        def _raise(*args, **kwargs):
            raise ConnectionRefusedError("Redis is down")

        events: list = []
        with patch.object(aioredis, "from_url", side_effect=_raise):
            from src.kamino.events import directive_event_subscriber
            async for event in directive_event_subscriber():
                events.append(event)  # pragma: no cover

        assert events == []
