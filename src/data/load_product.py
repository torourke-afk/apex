"""Product & Experience data loaders (APE-112 / APE-20b).

Read-only query functions over the DuckDB product domain tables:

    load_product_pipeline(status, product_area, priority)  → DataFrame
    load_roadmap(quarter, status, team)                    → DataFrame
    load_ab_tests(status, product_area)                    → DataFrame
    load_testing_velocity(team, weeks)                     → DataFrame
    get_pipeline_summary()                                 → dict
    get_velocity_baseline(team, weeks)                     → dict

Computed fields added by loaders:
    on_track        — initiative is meeting its success metric trajectory
    is_overdue      — initiative or roadmap item is past its target without completion
    is_significant  — A/B test p_value < 0.05 (derived from raw data)

Connections are opened and closed per call (no connection reuse across requests).

Tables queried:
    product_initiatives  — 15 strategic initiatives
    roadmap_items        — 12 roadmap deliverables (linked to initiatives)
    ab_tests             — 10 A/B experiments
    testing_velocity     — 12 weekly velocity snapshots
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import numpy as np
import pandas as pd

from src.data.init_db import get_connection
from src.data.seeds._dates import YESTERDAY

__all__ = [
    "load_product_pipeline",
    "load_roadmap",
    "load_ab_tests",
    "load_testing_velocity",
    "get_pipeline_summary",
    "get_velocity_baseline",
]

# Reference date used for on_track / is_overdue computations
_TODAY = YESTERDAY

# Quarter-end lookup — dynamically covers the year of _TODAY and the prior year
def _build_quarter_ends() -> dict[str, date]:
    """Build quarter-end mapping for the current and previous year."""
    ends: dict[str, date] = {}
    for y in (_TODAY.year - 1, _TODAY.year, _TODAY.year + 1):
        ends[f"{y}-Q1"] = date(y, 3, 31)
        ends[f"{y}-Q2"] = date(y, 6, 30)
        ends[f"{y}-Q3"] = date(y, 9, 30)
        ends[f"{y}-Q4"] = date(y, 12, 31)
    return ends

_QUARTER_END: dict[str, date] = _build_quarter_ends()

_VALID_INITIATIVE_STATUSES = frozenset({"discovery", "in_progress", "launched", "paused", "cancelled"})
_VALID_INITIATIVE_PRIORITIES = frozenset({"p0", "p1", "p2", "p3"})
_VALID_ROADMAP_STATUSES = frozenset({"planned", "in_flight", "complete", "deferred"})
_VALID_AB_STATUSES = frozenset({"draft", "running", "complete", "stopped"})


# ---------------------------------------------------------------------------
# Computed field helpers
# ---------------------------------------------------------------------------

def _compute_initiative_on_track(df: pd.DataFrame) -> pd.Series:
    """Return a boolean Series: True when the initiative is meeting its target.

    Rules:
    - launched: actual_value >= target_value
    - in_progress / discovery: target_launch_date >= today (still has runway)
    - paused / cancelled: False
    """
    launched_mask = df["status"] == "launched"
    active_mask = df["status"].isin({"in_progress", "discovery"})

    on_track = pd.Series(False, index=df.index)
    # Launched → compare actuals
    on_track.loc[launched_mask] = (
        df.loc[launched_mask, "actual_value"].notna()
        & (df.loc[launched_mask, "actual_value"] >= df.loc[launched_mask, "target_value"])
    )
    # Active → still within target window
    if active_mask.any():
        target_dates = pd.to_datetime(df.loc[active_mask, "target_launch_date"]).dt.date
        on_track.loc[active_mask] = target_dates >= _TODAY

    return on_track


def _compute_initiative_is_overdue(df: pd.DataFrame) -> pd.Series:
    """Return a boolean Series: True when an initiative is past its target date
    without having launched or been cancelled."""
    active_mask = df["status"].isin({"in_progress", "discovery", "paused"})
    target_dates = pd.to_datetime(df["target_launch_date"]).dt.date
    return active_mask & (target_dates < _TODAY)


def _compute_roadmap_is_overdue(df: pd.DataFrame) -> pd.Series:
    """Return a boolean Series for roadmap items: True when the quarter has
    ended and the item is not complete or deferred."""
    incomplete_mask = ~df["status"].isin({"complete", "deferred"})
    quarter_end = df["quarter"].map(lambda q: _QUARTER_END.get(q, date(9999, 12, 31)))
    return incomplete_mask & (quarter_end < _TODAY)


def _compute_ab_is_significant(df: pd.DataFrame) -> pd.Series:
    """Return a boolean Series: True when p_value < 0.05 (or is_significant is set)."""
    result = pd.Series(False, index=df.index)
    # Prefer the stored flag when present
    flag_mask = df["is_significant"].notna()
    result.loc[flag_mask] = df.loc[flag_mask, "is_significant"].astype(bool)
    # Derive from p_value where flag is absent
    no_flag_mask = ~flag_mask & df["p_value"].notna()
    result.loc[no_flag_mask] = df.loc[no_flag_mask, "p_value"].astype(float) < 0.05
    return result


# ---------------------------------------------------------------------------
# 1. load_product_pipeline
# ---------------------------------------------------------------------------

def load_product_pipeline(
    status: Optional[str] = None,
    product_area: Optional[str] = None,
    priority: Optional[str] = None,
) -> pd.DataFrame:
    """Load product initiatives with computed on_track and is_overdue flags.

    Args:
        status:       Filter by initiative status (discovery, in_progress,
                      launched, paused, cancelled).
        product_area: Filter by product area (e.g. 'checking', 'mortgage').
        priority:     Filter by priority (p0, p1, p2, p3).

    Returns:
        DataFrame with columns:
            id, title, description, status, priority, product_area, owner,
            target_launch_date, actual_launch_date, hypothesis, success_metric,
            baseline_value, target_value, actual_value,
            on_track (bool), is_overdue (bool),
            created_at, updated_at
    """
    if status is not None and status not in _VALID_INITIATIVE_STATUSES:
        raise ValueError(f"status must be one of {sorted(_VALID_INITIATIVE_STATUSES)}, got {status!r}")
    if priority is not None and priority not in _VALID_INITIATIVE_PRIORITIES:
        raise ValueError(f"priority must be one of {sorted(_VALID_INITIATIVE_PRIORITIES)}, got {priority!r}")

    filters: list[str] = []
    params: list = []
    if status is not None:
        filters.append("status = ?")
        params.append(status)
    if product_area is not None:
        filters.append("product_area = ?")
        params.append(product_area)
    if priority is not None:
        filters.append("priority = ?")
        params.append(priority)
    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    conn = get_connection()
    try:
        rows = conn.execute(
            f"""
            SELECT
                CAST(id AS VARCHAR)               AS id,
                title,
                description,
                status,
                priority,
                product_area,
                owner,
                target_launch_date,
                actual_launch_date,
                hypothesis,
                success_metric,
                CAST(baseline_value AS DOUBLE)    AS baseline_value,
                CAST(target_value AS DOUBLE)      AS target_value,
                CAST(actual_value AS DOUBLE)      AS actual_value,
                created_at,
                updated_at
            FROM product_initiatives
            {where}
            ORDER BY
                CASE priority
                    WHEN 'p0' THEN 0
                    WHEN 'p1' THEN 1
                    WHEN 'p2' THEN 2
                    WHEN 'p3' THEN 3
                    ELSE 9
                END,
                target_launch_date
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    cols = [
        "id", "title", "description", "status", "priority", "product_area",
        "owner", "target_launch_date", "actual_launch_date", "hypothesis",
        "success_metric", "baseline_value", "target_value", "actual_value",
        "created_at", "updated_at",
    ]
    df = pd.DataFrame(rows, columns=cols)

    for col in ("baseline_value", "target_value", "actual_value"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["on_track"] = _compute_initiative_on_track(df)
    df["is_overdue"] = _compute_initiative_is_overdue(df)

    return df


# ---------------------------------------------------------------------------
# 2. load_roadmap
# ---------------------------------------------------------------------------

def load_roadmap(
    quarter: Optional[str] = None,
    status: Optional[str] = None,
    team: Optional[str] = None,
) -> pd.DataFrame:
    """Load roadmap items joined to their parent initiatives.

    Args:
        quarter: Filter by quarter label (e.g. '2026-Q2').
        status:  Filter by item status (planned, in_flight, complete, deferred).
        team:    Filter by responsible team name (exact match).

    Returns:
        DataFrame with columns:
            id, initiative_id, initiative_title, quarter, title, status, team,
            effort_points, priority, milestone,
            is_overdue (bool),
            created_at, updated_at
    """
    if status is not None and status not in _VALID_ROADMAP_STATUSES:
        raise ValueError(f"status must be one of {sorted(_VALID_ROADMAP_STATUSES)}, got {status!r}")

    filters: list[str] = []
    params: list = []
    if quarter is not None:
        filters.append("r.quarter = ?")
        params.append(quarter)
    if status is not None:
        filters.append("r.status = ?")
        params.append(status)
    if team is not None:
        filters.append("r.team = ?")
        params.append(team)
    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    conn = get_connection()
    try:
        rows = conn.execute(
            f"""
            SELECT
                CAST(r.id AS VARCHAR)              AS id,
                CAST(r.initiative_id AS VARCHAR)   AS initiative_id,
                i.title                            AS initiative_title,
                r.quarter,
                r.title,
                r.status,
                r.team,
                r.effort_points,
                r.priority,
                r.milestone,
                r.created_at,
                r.updated_at
            FROM roadmap_items r
            LEFT JOIN product_initiatives i ON i.id = r.initiative_id
            {where}
            ORDER BY r.quarter, r.effort_points DESC
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    cols = [
        "id", "initiative_id", "initiative_title", "quarter", "title",
        "status", "team", "effort_points", "priority", "milestone",
        "created_at", "updated_at",
    ]
    df = pd.DataFrame(rows, columns=cols)
    df["effort_points"] = df["effort_points"].astype(int)
    df["is_overdue"] = _compute_roadmap_is_overdue(df)

    return df


# ---------------------------------------------------------------------------
# 3. load_ab_tests
# ---------------------------------------------------------------------------

def load_ab_tests(
    status: Optional[str] = None,
    product_area: Optional[str] = None,
) -> pd.DataFrame:
    """Load A/B tests with a re-computed is_significant flag.

    Args:
        status:       Filter by test status (draft, running, complete, stopped).
        product_area: Filter by product area.

    Returns:
        DataFrame with columns:
            id, test_name, hypothesis, product_area, status, variant_count,
            start_date, end_date, sample_size, traffic_allocation_pct,
            primary_metric, control_rate, treatment_rate, lift_pct, p_value,
            is_significant (bool), winner,
            created_at, updated_at
    """
    if status is not None and status not in _VALID_AB_STATUSES:
        raise ValueError(f"status must be one of {sorted(_VALID_AB_STATUSES)}, got {status!r}")

    filters: list[str] = []
    params: list = []
    if status is not None:
        filters.append("status = ?")
        params.append(status)
    if product_area is not None:
        filters.append("product_area = ?")
        params.append(product_area)
    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    conn = get_connection()
    try:
        rows = conn.execute(
            f"""
            SELECT
                CAST(id AS VARCHAR)                       AS id,
                test_name,
                hypothesis,
                product_area,
                status,
                variant_count,
                start_date,
                end_date,
                sample_size,
                CAST(traffic_allocation_pct AS DOUBLE)    AS traffic_allocation_pct,
                primary_metric,
                CAST(control_rate AS DOUBLE)              AS control_rate,
                CAST(treatment_rate AS DOUBLE)            AS treatment_rate,
                CAST(lift_pct AS DOUBLE)                  AS lift_pct,
                CAST(p_value AS DOUBLE)                   AS p_value,
                is_significant,
                winner,
                created_at,
                updated_at
            FROM ab_tests
            {where}
            ORDER BY start_date DESC
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    cols = [
        "id", "test_name", "hypothesis", "product_area", "status",
        "variant_count", "start_date", "end_date", "sample_size",
        "traffic_allocation_pct", "primary_metric",
        "control_rate", "treatment_rate", "lift_pct", "p_value",
        "is_significant", "winner",
        "created_at", "updated_at",
    ]
    df = pd.DataFrame(rows, columns=cols)

    for col in ("control_rate", "treatment_rate", "lift_pct", "p_value",
                "traffic_allocation_pct"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["variant_count"] = df["variant_count"].astype(int)
    df["sample_size"] = df["sample_size"].astype(int)

    # Re-derive is_significant from p_value so running tests update dynamically
    df["is_significant"] = _compute_ab_is_significant(df)

    return df


# ---------------------------------------------------------------------------
# 4. load_testing_velocity
# ---------------------------------------------------------------------------

def load_testing_velocity(
    team: Optional[str] = None,
    weeks: Optional[int] = None,
) -> pd.DataFrame:
    """Load testing velocity snapshots, most recent first.

    Args:
        team:  Filter by team name (exact match).
        weeks: Limit to the N most recent weeks. None returns all rows.

    Returns:
        DataFrame with columns:
            id, week_start, team, tests_launched, tests_completed,
            tests_running, winner_rate, avg_test_duration_days,
            total_sample_size, created_at, updated_at
    """
    if weeks is not None and (not isinstance(weeks, int) or weeks < 1):
        raise ValueError(f"weeks must be a positive integer, got {weeks!r}")

    filters: list[str] = []
    params: list = []
    if team is not None:
        filters.append("team = ?")
        params.append(team)
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    limit_clause = f"LIMIT {int(weeks)}" if weeks is not None else ""

    conn = get_connection()
    try:
        rows = conn.execute(
            f"""
            SELECT
                CAST(id AS VARCHAR)              AS id,
                week_start,
                team,
                tests_launched,
                tests_completed,
                tests_running,
                CAST(winner_rate AS DOUBLE)      AS winner_rate,
                avg_test_duration_days,
                total_sample_size,
                created_at,
                updated_at
            FROM testing_velocity
            {where}
            ORDER BY week_start DESC
            {limit_clause}
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    cols = [
        "id", "week_start", "team", "tests_launched", "tests_completed",
        "tests_running", "winner_rate", "avg_test_duration_days",
        "total_sample_size", "created_at", "updated_at",
    ]
    df = pd.DataFrame(rows, columns=cols)

    for col in ("tests_launched", "tests_completed", "tests_running",
                "avg_test_duration_days", "total_sample_size"):
        df[col] = df[col].astype(int)
    df["winner_rate"] = df["winner_rate"].astype(float)

    return df


# ---------------------------------------------------------------------------
# 5. get_pipeline_summary
# ---------------------------------------------------------------------------

def get_pipeline_summary() -> dict:
    """Aggregate summary of the product initiative pipeline.

    Returns:
        dict with keys:
            total_initiatives          (int)
            by_status                  (dict[str, int])   counts per status
            by_priority                (dict[str, int])   counts per priority
            by_product_area            (dict[str, int])   counts per area
            launched_count             (int)
            on_track_count             (int)   launched with actual >= target
            overdue_count              (int)   active past target date
            avg_target_value           (float)
            avg_actual_value           (float) launched initiatives only
            total_effort_points        (int)   sum of roadmap item effort
            roadmap_by_status          (dict[str, int])   roadmap counts per status
            ab_tests_running           (int)
            ab_tests_significant       (int)   complete tests with significant result
    """
    df = load_product_pipeline()
    road_df = load_roadmap()
    ab_df = load_ab_tests()

    launched_df = df[df["status"] == "launched"]

    by_status = df["status"].value_counts().to_dict()
    by_priority = df["priority"].value_counts().to_dict()
    by_area = df["product_area"].value_counts().to_dict()

    avg_actual = float(launched_df["actual_value"].mean()) if not launched_df.empty else 0.0
    avg_target = float(df["target_value"].mean()) if not df.empty else 0.0

    return {
        "total_initiatives": len(df),
        "by_status": by_status,
        "by_priority": by_priority,
        "by_product_area": by_area,
        "launched_count": int((df["status"] == "launched").sum()),
        "on_track_count": int(df["on_track"].sum()),
        "overdue_count": int(df["is_overdue"].sum()),
        "avg_target_value": round(avg_target, 6),
        "avg_actual_value": round(avg_actual, 6),
        "total_effort_points": int(road_df["effort_points"].sum()),
        "roadmap_by_status": road_df["status"].value_counts().to_dict(),
        "ab_tests_running": int((ab_df["status"] == "running").sum()),
        "ab_tests_significant": int(
            ((ab_df["status"] == "complete") & ab_df["is_significant"]).sum()
        ),
    }


# ---------------------------------------------------------------------------
# 6. get_velocity_baseline
# ---------------------------------------------------------------------------

def get_velocity_baseline(
    team: Optional[str] = None,
    weeks: int = 12,
) -> dict:
    """Compute baseline testing velocity metrics over a trailing window.

    Args:
        team:  Team to scope baseline to. None aggregates all teams.
        weeks: Number of most recent weekly rows to include. Default 12.

    Returns:
        dict with keys:
            team                     (str | None)
            weeks_included           (int)
            avg_tests_launched       (float)
            avg_tests_completed      (float)
            avg_tests_running        (float)
            avg_winner_rate          (float)
            avg_test_duration_days   (float)
            avg_total_sample_size    (float)
            total_tests_launched     (int)
            total_tests_completed    (int)
            winner_rate_trend        (float)  linear slope (signal/week), positive = improving
    """
    df = load_testing_velocity(team=team, weeks=weeks)

    if df.empty:
        return {
            "team": team,
            "weeks_included": 0,
            "avg_tests_launched": 0.0,
            "avg_tests_completed": 0.0,
            "avg_tests_running": 0.0,
            "avg_winner_rate": 0.0,
            "avg_test_duration_days": 0.0,
            "avg_total_sample_size": 0.0,
            "total_tests_launched": 0,
            "total_tests_completed": 0,
            "winner_rate_trend": 0.0,
        }

    # Chronological order for trend calculation
    df_sorted = df.sort_values("week_start")
    winner_rate_trend = 0.0
    if len(df_sorted) >= 2:
        xs = np.arange(len(df_sorted), dtype=float)
        ys = df_sorted["winner_rate"].to_numpy(dtype=float)
        slope, _ = np.polyfit(xs, ys, 1)
        winner_rate_trend = float(round(slope, 6))

    return {
        "team": team,
        "weeks_included": len(df),
        "avg_tests_launched": round(float(df["tests_launched"].mean()), 4),
        "avg_tests_completed": round(float(df["tests_completed"].mean()), 4),
        "avg_tests_running": round(float(df["tests_running"].mean()), 4),
        "avg_winner_rate": round(float(df["winner_rate"].mean()), 4),
        "avg_test_duration_days": round(float(df["avg_test_duration_days"].mean()), 4),
        "avg_total_sample_size": round(float(df["total_sample_size"].mean()), 2),
        "total_tests_launched": int(df["tests_launched"].sum()),
        "total_tests_completed": int(df["tests_completed"].sum()),
        "winner_rate_trend": winner_rate_trend,
    }
