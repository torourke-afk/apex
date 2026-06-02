"""pytest configuration for the Apex test suite.

DuckDB DELETE pre-commit
------------------------
DuckDB 1.x evaluates foreign-key constraints against the *committed* database
state, not the pending writes of the current transaction.  This means:

    DELETE FROM sem_daily_performance   ← deletes rows (uncommitted)
    DELETE FROM sem_keyword_groups      ← FK check still sees old rows → ERROR

We attach a ``before_cursor_execute`` event listener that issues a DBAPI-level
COMMIT immediately before *any* DELETE on a DuckDB connection.  This ensures:

1. FK-parent table deletes always see committed child-row deletions.
2. db_session fixture teardown reliably clears rows between test classes —
   without a pre-commit, the session may be in a partially-committed state
   that prevents the cleanup DELETE from taking effect, causing subsequent
   tests to see stale rows.
"""

import sys

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine


@pytest.fixture(scope="session", autouse=True)
def _preload_streamlit():
    """Import streamlit once at session start so it is always in sys.modules.

    ``_restore_streamlit_module`` saves ``sys.modules.get("streamlit")`` before
    each test.  If that value is None (streamlit not yet loaded), the fixture
    removes streamlit from sys.modules after the test.  A subsequent test that
    then tries to ``import streamlit`` for the first time re-runs
    ``streamlit/__init__.py`` against already-loaded submodules, causing
    ``DeltaGeneratorSingleton`` to raise RuntimeError ("instance already exists").

    By pre-loading streamlit at session scope, ``_restore_streamlit_module``
    always sees a non-None original and restores rather than removes it, keeping
    streamlit consistently available across all tests.
    """
    import streamlit  # noqa: F401


@pytest.fixture(autouse=True)
def _restore_streamlit_module():
    """Save and restore ``sys.modules["streamlit"]`` around every test.

    ``test_simulator_ui_helpers.py`` replaces ``sys.modules["streamlit"]`` with
    a lightweight fake and never restores it.  Without this fixture the fake
    persists into later test files.  Modules that cached the real streamlit
    reference at import time (e.g. ``src.state``) then diverge from what
    ``import streamlit`` returns in those later files, splitting monkeypatches
    across two objects and causing 8 ``test_state.py`` tests to fail in the
    full suite even though they pass in isolation.
    """
    original = sys.modules.get("streamlit")
    yield
    if original is None:
        sys.modules.pop("streamlit", None)
    else:
        sys.modules["streamlit"] = original


@event.listens_for(Engine, "before_cursor_execute")
def _duckdb_pre_commit_before_delete(
    conn, cursor, statement, parameters, context, executemany
):
    """Commit pending writes before any DELETE in DuckDB.

    Covers both FK-parent teardown ordering and general test-isolation
    cleanup so that db_session fixture teardown always runs against a
    clean, committed connection state.
    """
    if getattr(conn.engine.dialect, "name", "") != "duckdb":
        return
    if statement.strip().upper().startswith("DELETE"):
        try:
            cursor.connection.commit()
        except Exception:
            pass
