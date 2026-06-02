"""Tests for src/kamino/client.py.

Uses httpx's built-in mock transport so no real HTTP calls are made.
pytest-asyncio runs the async test functions.
"""
from __future__ import annotations

import json
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.kamino.client import (
    JobCancelResponse,
    JobStatusResponse,
    JobSubmitResponse,
    KaminoAuthError,
    KaminoClient,
    KaminoHTTPError,
    KaminoNotFoundError,
    KaminoRetryExhaustedError,
    KaminoTimeoutError,
)
from src.kamino.models import DirectivePayload, DirectiveStatus, DirectiveType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_JOB_ID = "job-abc-123"
_BASE_UUID = str(uuid.uuid4())


def _make_directive_payload() -> DirectivePayload:
    return DirectivePayload(
        type=DirectiveType.budget_reallocation,
        parameters={"channel": "sem", "delta_pct": 10},
        description="Shift 10% budget to SEM",
        source_module="paid_channels",
    )


def _json_response(data: dict[str, Any], status_code: int = 200) -> httpx.Response:
    """Build a minimal httpx.Response with a JSON body."""
    return httpx.Response(
        status_code=status_code,
        headers={"content-type": "application/json"},
        text=json.dumps(data),
    )


def _client_with_mock(mock_response_or_side_effect) -> tuple[KaminoClient, AsyncMock]:
    """Return a KaminoClient whose _client.request is mocked.

    Avoids real network calls without needing a custom transport.
    """
    client = KaminoClient(
        base_url="http://kamino.test",
        api_key="test-key",
        max_retries=3,
        backoff_base=0.0,  # zero so tests run instantly
    )
    mock = AsyncMock()
    if isinstance(mock_response_or_side_effect, list):
        mock.side_effect = mock_response_or_side_effect
    else:
        mock.return_value = mock_response_or_side_effect
    client._client.request = mock
    return client, mock


# ---------------------------------------------------------------------------
# submit_directive
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_submit_directive_success():
    job_id = _JOB_ID
    response_data = {
        "id": _BASE_UUID,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
        "job_id": job_id,
        "status": "pending",
        "message": "queued",
    }
    client, mock = _client_with_mock(_json_response(response_data))

    result = await client.submit_directive(_make_directive_payload())

    assert isinstance(result, JobSubmitResponse)
    assert result.job_id == job_id
    assert result.status == DirectiveStatus.pending
    assert result.message == "queued"
    mock.assert_awaited_once()
    call_args = mock.call_args
    assert call_args[0][0] == "POST"
    assert "/directives" in call_args[0][1]


@pytest.mark.asyncio
async def test_submit_directive_sends_json_body():
    response_data = {
        "id": _BASE_UUID,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
        "job_id": _JOB_ID,
        "status": "pending",
    }
    client, mock = _client_with_mock(_json_response(response_data))
    payload = _make_directive_payload()

    await client.submit_directive(payload)

    _, kwargs = mock.call_args
    body = json.loads(kwargs["content"])
    assert body["type"] == "budget_reallocation"
    assert body["source_module"] == "paid_channels"


# ---------------------------------------------------------------------------
# check_job_status
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_job_status_success():
    response_data = {
        "id": _BASE_UUID,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
        "job_id": _JOB_ID,
        "status": "in_progress",
        "started_at": "2026-01-01T00:01:00",
        "completed_at": None,
        "failure_reason": None,
        "result": None,
    }
    client, mock = _client_with_mock(_json_response(response_data))

    result = await client.check_job_status(_JOB_ID)

    assert isinstance(result, JobStatusResponse)
    assert result.job_id == _JOB_ID
    assert result.status == DirectiveStatus.in_progress
    call_args = mock.call_args
    assert call_args[0][0] == "GET"
    assert f"/jobs/{_JOB_ID}" in call_args[0][1]


@pytest.mark.asyncio
async def test_check_job_status_completed():
    response_data = {
        "id": _BASE_UUID,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
        "job_id": _JOB_ID,
        "status": "completed",
        "started_at": "2026-01-01T00:01:00",
        "completed_at": "2026-01-01T00:02:00",
        "failure_reason": None,
        "result": {"applied": True},
    }
    client, mock = _client_with_mock(_json_response(response_data))

    result = await client.check_job_status(_JOB_ID)

    assert result.status == DirectiveStatus.completed
    assert result.result == {"applied": True}


# ---------------------------------------------------------------------------
# cancel_job
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cancel_job_success():
    response_data = {
        "id": _BASE_UUID,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
        "job_id": _JOB_ID,
        "status": "cancelled",
        "message": "job cancelled",
    }
    client, mock = _client_with_mock(_json_response(response_data))

    result = await client.cancel_job(_JOB_ID)

    assert isinstance(result, JobCancelResponse)
    assert result.status == DirectiveStatus.cancelled
    call_args = mock.call_args
    assert call_args[0][0] == "DELETE"
    assert f"/jobs/{_JOB_ID}" in call_args[0][1]


# ---------------------------------------------------------------------------
# Error handling — HTTP status codes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_raises_kamino_auth_error_on_401():
    client, mock = _client_with_mock(_json_response({"detail": "Unauthorized"}, 401))
    with pytest.raises(KaminoAuthError) as exc_info:
        await client.check_job_status(_JOB_ID)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_raises_kamino_auth_error_on_403():
    client, mock = _client_with_mock(_json_response({"detail": "Forbidden"}, 403))
    with pytest.raises(KaminoAuthError) as exc_info:
        await client.check_job_status(_JOB_ID)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_raises_kamino_not_found_error_on_404():
    client, mock = _client_with_mock(_json_response({"detail": "Not found"}, 404))
    with pytest.raises(KaminoNotFoundError) as exc_info:
        await client.check_job_status("nonexistent-id")
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_raises_kamino_http_error_on_400():
    client, mock = _client_with_mock(_json_response({"detail": "Bad request"}, 400))
    with pytest.raises(KaminoHTTPError) as exc_info:
        await client.submit_directive(_make_directive_payload())
    assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Retry logic — transient 5xx
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retries_on_503_then_succeeds():
    """Client retries once on 503 and succeeds on the second attempt."""
    success_data = {
        "id": _BASE_UUID,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
        "job_id": _JOB_ID,
        "status": "pending",
    }
    client, mock = _client_with_mock([
        _json_response({"detail": "Service Unavailable"}, 503),
        _json_response(success_data, 200),
    ])

    result = await client.submit_directive(_make_directive_payload())

    assert result.status == DirectiveStatus.pending
    assert mock.await_count == 2


@pytest.mark.asyncio
async def test_retries_on_429_then_succeeds():
    success_data = {
        "id": _BASE_UUID,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
        "job_id": _JOB_ID,
        "status": "in_progress",
    }
    client, mock = _client_with_mock([
        _json_response({}, 429),
        _json_response(success_data, 200),
    ])

    result = await client.check_job_status(_JOB_ID)

    assert result.status == DirectiveStatus.in_progress
    assert mock.await_count == 2


@pytest.mark.asyncio
async def test_exhausts_retries_raises_retry_exhausted():
    """All attempts return 503 → KaminoRetryExhaustedError after max_retries+1 calls."""
    client, mock = _client_with_mock(
        [_json_response({}, 503)] * 4  # max_retries=3 → 4 total attempts
    )

    with pytest.raises(KaminoRetryExhaustedError):
        await client.check_job_status(_JOB_ID)

    assert mock.await_count == 4  # initial + 3 retries


@pytest.mark.asyncio
async def test_does_not_retry_on_404():
    """404 is not a transient error — must not retry."""
    client, mock = _client_with_mock(_json_response({"detail": "Not found"}, 404))

    with pytest.raises(KaminoNotFoundError):
        await client.check_job_status("bad-id")

    assert mock.await_count == 1


# ---------------------------------------------------------------------------
# Retry logic — timeouts
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retries_on_timeout_then_succeeds():
    success_data = {
        "id": _BASE_UUID,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
        "job_id": _JOB_ID,
        "status": "pending",
    }
    client, mock = _client_with_mock([
        httpx.TimeoutException("timed out"),
        _json_response(success_data, 200),
    ])

    result = await client.submit_directive(_make_directive_payload())

    assert result.job_id == _JOB_ID
    assert mock.await_count == 2


@pytest.mark.asyncio
async def test_exhausts_retries_on_repeated_timeout():
    client, mock = _client_with_mock(
        [httpx.TimeoutException("timed out")] * 4
    )

    with pytest.raises(KaminoRetryExhaustedError):
        await client.cancel_job(_JOB_ID)

    assert mock.await_count == 4


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_context_manager_closes_client():
    """__aexit__ must call aclose on the underlying httpx client."""
    async with KaminoClient(base_url="http://kamino.test", api_key="k") as client:
        close_mock = AsyncMock()
        client._client.aclose = close_mock

    close_mock.assert_awaited_once()


# ---------------------------------------------------------------------------
# Auth header
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bearer_token_sent_in_headers():
    """The Authorization header must contain the configured API key."""
    success_data = {
        "id": _BASE_UUID,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
        "job_id": _JOB_ID,
        "status": "pending",
    }
    client = KaminoClient(base_url="http://kamino.test", api_key="my-secret-key")
    mock = AsyncMock(return_value=_json_response(success_data))
    client._client.request = mock

    await client.check_job_status(_JOB_ID)

    # The Authorization header is set on the underlying client, not per-request kwargs,
    # so we verify it was configured at construction time.
    assert client._client.headers["authorization"] == "Bearer my-secret-key"


# ---------------------------------------------------------------------------
# Environment variable fallback (module-level constants)
# ---------------------------------------------------------------------------

def test_kamino_api_url_env_default(monkeypatch):
    monkeypatch.delenv("KAMINO_API_URL", raising=False)
    import importlib
    import src.kamino.client as mod
    importlib.reload(mod)
    assert mod.KAMINO_API_URL == "http://localhost:8001"


def test_kamino_api_url_env_override(monkeypatch):
    monkeypatch.setenv("KAMINO_API_URL", "https://kamino.prod.example.com")
    import importlib
    import src.kamino.client as mod
    importlib.reload(mod)
    assert mod.KAMINO_API_URL == "https://kamino.prod.example.com"
    monkeypatch.delenv("KAMINO_API_URL")
    importlib.reload(mod)  # restore default


def test_kamino_api_key_env_override(monkeypatch):
    monkeypatch.setenv("KAMINO_API_KEY", "prod-api-key-xyz")
    import importlib
    import src.kamino.client as mod
    importlib.reload(mod)
    assert mod.KAMINO_API_KEY == "prod-api-key-xyz"
    monkeypatch.delenv("KAMINO_API_KEY")
    importlib.reload(mod)
