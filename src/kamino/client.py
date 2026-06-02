"""Async HTTP client for the Kamino directive bus API."""
from __future__ import annotations

import asyncio
import os
from typing import Any, Optional

import httpx

from src.kamino.models import DirectivePayload, DirectiveStatus
from src.models.base import ApexBase


# ---------------------------------------------------------------------------
# Settings (read from environment)
# ---------------------------------------------------------------------------

KAMINO_API_URL: str = os.getenv("KAMINO_API_URL", "http://localhost:8001")
KAMINO_API_KEY: str = os.getenv("KAMINO_API_KEY", "")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class KaminoError(Exception):
    """Base exception for all Kamino client errors."""


class KaminoHTTPError(KaminoError):
    """Non-success HTTP response from the Kamino API."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code
        self.message = message


class KaminoAuthError(KaminoHTTPError):
    """Authentication / authorisation failure (401 or 403)."""


class KaminoNotFoundError(KaminoHTTPError):
    """Job or resource not found (404)."""


class KaminoTimeoutError(KaminoError):
    """Request timed out before a response was received."""


class KaminoRetryExhaustedError(KaminoError):
    """All retry attempts were exhausted without a successful response."""


# ---------------------------------------------------------------------------
# Response models (Pydantic, not ORM-backed)
# ---------------------------------------------------------------------------


class JobSubmitResponse(ApexBase):
    """Envelope returned when a directive is submitted to Kamino."""

    job_id: str
    status: DirectiveStatus
    message: Optional[str] = None


class JobStatusResponse(ApexBase):
    """Current state of a Kamino job."""

    job_id: str
    status: DirectiveStatus
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    failure_reason: Optional[str] = None
    result: Optional[dict[str, Any]] = None


class JobCancelResponse(ApexBase):
    """Envelope returned after a cancel request."""

    job_id: str
    status: DirectiveStatus
    message: Optional[str] = None


# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------

_RETRY_STATUSES: frozenset[int] = frozenset({429, 500, 502, 503, 504})
_DEFAULT_MAX_RETRIES: int = 3
_DEFAULT_BACKOFF_BASE: float = 1.0  # seconds; doubles each attempt


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class KaminoClient:
    """Async HTTP client for the Kamino directive bus API.

    Usage::

        async with KaminoClient() as client:
            resp = await client.submit_directive(payload)

    Constructor keyword arguments override the corresponding environment
    variables (``KAMINO_API_URL``, ``KAMINO_API_KEY``).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        backoff_base: float = _DEFAULT_BACKOFF_BASE,
        timeout: float = 30.0,
        # Allow injecting a transport for testing without real HTTP calls.
        _transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self.base_url = (base_url or KAMINO_API_URL).rstrip("/")
        self.api_key = api_key or KAMINO_API_KEY
        self.max_retries = max_retries
        self.backoff_base = backoff_base

        client_kwargs: dict[str, Any] = {
            "base_url": self.base_url,
            "headers": {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            "timeout": timeout,
        }
        if _transport is not None:
            client_kwargs["transport"] = _transport

        self._client = httpx.AsyncClient(**client_kwargs)

    async def __aenter__(self) -> "KaminoClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Send *method* *path* with exponential-backoff retry.

        Retries on transient HTTP status codes (429, 5xx) and on
        ``httpx.TimeoutException``.  Raises :class:`KaminoRetryExhaustedError`
        when all attempts fail.
        """
        last_exc: Optional[Exception] = None

        last_response: Optional[httpx.Response] = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.request(method, path, **kwargs)
            except httpx.TimeoutException as exc:
                last_exc = KaminoTimeoutError(str(exc))
                if attempt < self.max_retries:
                    await asyncio.sleep(self.backoff_base * (2 ** attempt))
                    continue
                break

            if response.status_code in _RETRY_STATUSES:
                last_response = response
                if attempt < self.max_retries:
                    await asyncio.sleep(self.backoff_base * (2 ** attempt))
                    continue
                # Final attempt also returned a retry-eligible status.
                break

            self._raise_for_status(response)
            return response

        raise KaminoRetryExhaustedError(
            f"Exhausted {self.max_retries} retries for {method} {path}"
        ) from last_exc

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        """Translate error HTTP status codes to typed exceptions."""
        code = response.status_code
        if code in (401, 403):
            raise KaminoAuthError(code, response.text)
        if code == 404:
            raise KaminoNotFoundError(code, response.text)
        if code >= 400:
            raise KaminoHTTPError(code, response.text)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def submit_directive(self, payload: DirectivePayload) -> JobSubmitResponse:
        """Submit a directive to the Kamino bus.

        Args:
            payload: Validated :class:`~src.kamino.models.DirectivePayload`.

        Returns:
            :class:`JobSubmitResponse` with the assigned ``job_id`` and
            initial ``status``.
        """
        response = await self._request(
            "POST",
            "/directives",
            content=payload.model_dump_json(),
        )
        return JobSubmitResponse.model_validate(response.json())

    async def check_job_status(self, job_id: str) -> JobStatusResponse:
        """Fetch the current status of a Kamino job.

        Args:
            job_id: Opaque job identifier returned by :meth:`submit_directive`.

        Returns:
            :class:`JobStatusResponse` with status and optional timestamps.

        Raises:
            :class:`KaminoNotFoundError`: If *job_id* does not exist.
        """
        response = await self._request("GET", f"/jobs/{job_id}")
        return JobStatusResponse.model_validate(response.json())

    async def cancel_job(self, job_id: str) -> JobCancelResponse:
        """Cancel a pending or in-progress Kamino job.

        Args:
            job_id: Opaque job identifier returned by :meth:`submit_directive`.

        Returns:
            :class:`JobCancelResponse` confirming the cancellation.

        Raises:
            :class:`KaminoNotFoundError`: If *job_id* does not exist.
        """
        response = await self._request("DELETE", f"/jobs/{job_id}")
        return JobCancelResponse.model_validate(response.json())
