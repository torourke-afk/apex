"""
Scenario Engine
---------------
Manages named budget scenarios in both st.session_state (for fast UI re-renders)
and the DuckDB `scenarios` table (for persistence across sessions).

Public API
----------
init_scenario_state()           — seed session_state keys once per page load
save_scenario(scenario_dict)    — write to session_state + DuckDB
delete_scenario(name)           — remove from session_state + DuckDB
load_scenarios_from_db()        — bulk-load DuckDB → session_state on cold start
get_scenarios()                 — return current list[dict] from session_state
snapshot_current_state(...)     — build a scenario dict from live page controls
"""

from __future__ import annotations

import json
import datetime
from typing import Any

import streamlit as st

from src.data.init_db import get_connection, init_db

_SESSION_KEY = "spend_scenarios"


def _ensure_tables() -> None:
    """Create scenarios/directives tables if they don't exist."""
    init_db()


# ---------------------------------------------------------------------------
# Session-state bootstrap
# ---------------------------------------------------------------------------

def init_scenario_state() -> None:
    """
    Call once at the top of the page.
    Seeds session_state keys and loads persisted scenarios from DuckDB
    on a cold start (first run in this session).
    """
    if _SESSION_KEY not in st.session_state:
        st.session_state[_SESSION_KEY] = []
        # Cold start — populate from DB
        _ensure_tables()
        rows = _fetch_all_from_db()
        st.session_state[_SESSION_KEY] = rows

    if "submitted_directives" not in st.session_state:
        st.session_state["submitted_directives"] = []


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _fetch_all_from_db() -> list[dict]:
    """Return all scenarios ordered by id ascending."""
    conn = get_connection()
    try:
        result = conn.execute(
            "SELECT payload FROM scenarios ORDER BY id ASC"
        ).fetchall()
        return [json.loads(row[0]) for row in result]
    except Exception:
        return []
    finally:
        conn.close()


def _next_id(conn, table: str) -> int:
    row = conn.execute(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table}").fetchone()
    return int(row[0]) if row else 1


# ---------------------------------------------------------------------------
# Public CRUD
# ---------------------------------------------------------------------------

def get_scenarios() -> list[dict]:
    """Return current scenarios from session_state."""
    return list(st.session_state.get(_SESSION_KEY, []))


def save_scenario(scenario: dict) -> tuple[bool, str]:
    """
    Save or overwrite a named scenario.

    Returns (success: bool, message: str).
    Limit: 3 scenarios max.
    """
    _ensure_tables()
    name = scenario.get("name", "").strip()
    if not name:
        return False, "Scenario name cannot be empty."

    current = get_scenarios()
    existing_names = [s["name"] for s in current]

    if name not in existing_names and len(current) >= 3:
        return False, "Maximum of 3 scenarios reached. Remove one first."

    # Update session_state
    if name in existing_names:
        idx = existing_names.index(name)
        updated = list(current)
        updated[idx] = scenario
        st.session_state[_SESSION_KEY] = updated
    else:
        st.session_state[_SESSION_KEY] = current + [scenario]

    # Upsert into DuckDB
    conn = get_connection()
    try:
        payload_json = json.dumps(scenario)
        # Check if row exists
        row = conn.execute(
            "SELECT id FROM scenarios WHERE name = ?", [name]
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE scenarios SET payload = ?, created_at = CURRENT_TIMESTAMP WHERE name = ?",
                [payload_json, name],
            )
        else:
            new_id = _next_id(conn, "scenarios")
            conn.execute(
                "INSERT INTO scenarios (id, name, payload) VALUES (?, ?, ?)",
                [new_id, name, payload_json],
            )
        conn.commit()
    except Exception as exc:
        return False, f"DB error: {exc}"
    finally:
        conn.close()

    return True, f"Scenario '{name}' saved."


def delete_scenario(name: str) -> None:
    """Remove a scenario by name from session_state and DuckDB."""
    current = get_scenarios()
    st.session_state[_SESSION_KEY] = [s for s in current if s["name"] != name]

    _ensure_tables()
    conn = get_connection()
    try:
        conn.execute("DELETE FROM scenarios WHERE name = ?", [name])
        conn.commit()
    finally:
        conn.close()


def clear_all_scenarios() -> None:
    """Remove all scenarios from session_state and DuckDB."""
    st.session_state[_SESSION_KEY] = []
    _ensure_tables()
    conn = get_connection()
    try:
        conn.execute("DELETE FROM scenarios")
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Snapshot builder
# ---------------------------------------------------------------------------

def snapshot_current_state(
    name: str,
    brand_shift: float,
    sem_shift: float,
    social_shift: float,
    markets_added: int,
    life_events: bool,
    branded_sem_pct: float,
    channel_overrides: dict[str, Any] | None = None,
    tier_overrides: dict[str, int] | None = None,
) -> dict:
    """
    Build a scenario dict from live page-control values.

    The payload captures:
      - human-readable budget line items and projected KPIs
      - raw channel mix overrides (per-product weights)
      - raw market tier overrides (DMA → tier)

    This ensures round-trip fidelity when comparing or submitting.
    """
    baseline_cpihh = 312.0
    baseline_retention = 84.3
    baseline_brand = 68.5

    total_shift = brand_shift + sem_shift + social_shift
    cpihh_proj = baseline_cpihh * (1 - total_shift * 0.008)
    retention_proj = baseline_retention + markets_added * 0.3 + (0.8 if life_events else 0.0)
    brand_proj = baseline_brand + brand_shift * 1.2

    return {
        "name": name or "New Scenario",
        # Budget line items
        "Brand Media ($M)": round(10.0 + brand_shift, 1),
        "Perf. SEM ($M)": round(3.5 + sem_shift, 1),
        "Paid Social ($M)": round(2.5 + social_shift, 1),
        "Total Spend ($M)": round(21.0 + total_shift, 1),
        # Tactical controls
        "Tier-1 Markets": 10 + markets_added,
        "Life Events": "On" if life_events else "Off",
        "SEM Branded %": round(branded_sem_pct * 100, 0),
        # Projected KPIs
        "Proj. CPIHH": round(cpihh_proj, 0),
        "Proj. Retention": round(retention_proj, 1),
        "Proj. Brand Score": round(brand_proj, 1),
        # Raw state for round-trip fidelity
        "_channel_overrides": channel_overrides or {},
        "_tier_overrides": tier_overrides or {},
        "_captured_at": str(datetime.date.today()),
    }
