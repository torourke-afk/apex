"""Query counter utility (APE-131).

Wraps DuckDB execute() to count and optionally log queries per page/context.

Usage:

    from src.data.query_counter import QueryCounter

    counter = QueryCounter("Executive Scorecard")
    conn = get_connection()
    wrapped = counter.wrap(conn)

    # Use wrapped.execute() instead of conn.execute() for tracked calls.
    rows = wrapped.execute("SELECT ...").fetchall()

    counter.report()   # logs count when APEX_DEBUG_MODE=1

Environment:
    APEX_DEBUG_MODE=1  — enable query logging (default: off)

The counter is intentionally lightweight and has no production overhead when
debug mode is disabled.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_DEBUG_MODE: bool = os.environ.get("APEX_DEBUG_MODE", "").strip() in ("1", "true", "yes")


class _TrackedConnection:
    """Thin proxy around a DuckDB connection that increments a counter on each execute."""

    def __init__(self, conn: Any, counter: "QueryCounter") -> None:
        self._conn = conn
        self._counter = counter

    def execute(self, query: str, parameters: list | None = None) -> Any:
        self._counter._count += 1
        if _DEBUG_MODE:
            logger.debug(
                "[QueryCounter][%s] query #%d: %.120s",
                self._counter.page_name,
                self._counter._count,
                query.strip().replace("\n", " "),
            )
        if parameters is not None:
            return self._conn.execute(query, parameters)
        return self._conn.execute(query)

    def __getattr__(self, name: str) -> Any:
        # Delegate everything else (fetchall, df, close, commit, …) to the real conn.
        return getattr(self._conn, name)


class QueryCounter:
    """Count DB queries made during a single page render.

    Args:
        page_name: Human-readable label for log output (e.g. 'Executive Scorecard').

    Example::

        counter = QueryCounter("Spend Allocation")
        conn = get_connection()
        tracked = counter.wrap(conn)

        result = tracked.execute("SELECT ...").fetchall()
        counter.report()   # logs/warns if over budget
    """

    QUERY_BUDGET = 10  # target: <10 queries per full page load

    def __init__(self, page_name: str = "unknown") -> None:
        self.page_name = page_name
        self._count: int = 0

    @property
    def count(self) -> int:
        return self._count

    def reset(self) -> None:
        self._count = 0

    def wrap(self, conn: Any) -> _TrackedConnection:
        """Return a tracked proxy for *conn*."""
        return _TrackedConnection(conn, self)

    def report(self) -> None:
        """Log query count. Only emits output when APEX_DEBUG_MODE=1."""
        if not _DEBUG_MODE:
            return
        over = self._count > self.QUERY_BUDGET
        level = logging.WARNING if over else logging.INFO
        logger.log(
            level,
            "[QueryCounter][%s] %d queries (%s budget of %d)",
            self.page_name,
            self._count,
            "OVER" if over else "within",
            self.QUERY_BUDGET,
        )
