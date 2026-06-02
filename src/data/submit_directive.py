"""
Directive Submission
--------------------
Writes a budget directive (a committed scenario) to the DuckDB `directives`
table and mirrors it in st.session_state["submitted_directives"].

Public API
----------
submit_directive(scenario, note)  — insert into DB + update session_state
get_submitted_directives()        — return session_state list (most-recent first)
load_directives_from_db()         — bulk-load DB → session_state on cold start
"""

from __future__ import annotations

import json
import datetime

import streamlit as st

from src.data.init_db import get_connection

_SESSION_KEY = "submitted_directives"

_DIRECTIVES_DDL = """
CREATE TABLE IF NOT EXISTS directives (
    id            INTEGER PRIMARY KEY,
    scenario_name VARCHAR NOT NULL,
    payload       JSON    NOT NULL,
    note          VARCHAR DEFAULT '',
    submitted_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


def _ensure_table() -> None:
    conn = get_connection()
    try:
        conn.execute(_DIRECTIVES_DDL)
        conn.commit()
    finally:
        conn.close()


def _next_id(conn) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(id), 0) + 1 FROM directives"
    ).fetchone()
    return int(row[0]) if row else 1


# ---------------------------------------------------------------------------
# Session-state bootstrap
# ---------------------------------------------------------------------------

def init_directive_state() -> None:
    """
    Call once per page load.
    Seeds session_state and loads directives from DB on cold start.
    """
    if _SESSION_KEY not in st.session_state:
        st.session_state[_SESSION_KEY] = []
        _ensure_table()
        st.session_state[_SESSION_KEY] = load_directives_from_db()


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def load_directives_from_db() -> list[dict]:
    """Return all directives ordered newest-first."""
    _ensure_table()
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT scenario_name, payload, note, submitted_at "
            "FROM directives ORDER BY id DESC"
        ).fetchall()
        result = []
        for scenario_name, payload_json, note, submitted_at in rows:
            result.append({
                "scenario": json.loads(payload_json),
                "note": note or "",
                "submitted_at": str(submitted_at)[:10],  # date portion only
            })
        return result
    except Exception:
        return []
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Submit
# ---------------------------------------------------------------------------

def submit_directive(scenario: dict, note: str = "") -> tuple[bool, str]:
    """
    Persist a directive to DuckDB and prepend it to session_state.

    Returns (success: bool, message: str).
    """
    name = scenario.get("name", "").strip()
    if not name:
        return False, "Scenario has no name — cannot submit directive."

    _ensure_table()
    conn = get_connection()
    try:
        new_id = _next_id(conn)
        payload_json = json.dumps(scenario)
        conn.execute(
            "INSERT INTO directives (id, scenario_name, payload, note) VALUES (?, ?, ?, ?)",
            [new_id, name, payload_json, note or ""],
        )
        conn.commit()
    except Exception as exc:
        return False, f"DB error: {exc}"
    finally:
        conn.close()

    # Mirror in session_state (newest first)
    entry = {
        "scenario": scenario,
        "note": note or "",
        "submitted_at": str(datetime.date.today()),
    }
    current = list(st.session_state.get(_SESSION_KEY, []))
    st.session_state[_SESSION_KEY] = [entry] + current

    return True, f"Directive '{name}' submitted to Kamino bus."


# ---------------------------------------------------------------------------
# Accessor
# ---------------------------------------------------------------------------

def get_submitted_directives() -> list[dict]:
    """Return submitted directives from session_state (newest first)."""
    return list(st.session_state.get(_SESSION_KEY, []))
