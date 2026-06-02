"""Ops Command Center data loaders (APE-117 / APE-21c).

Read/write query functions over the DuckDB ops domain tables:

    load_calendar_events(month=None)             → DataFrame
    load_approval_queue(status=None)             → DataFrame
    load_system_health()                         → DataFrame
    load_competitive_feed(category=None, impact=None) → DataFrame
    load_team_capacity(period=None)              → DataFrame
    approve_item(item_id)                        → bool
    reject_item(item_id, reason=None)            → bool

Connections are opened and closed per call.
All loaders return correctly typed DataFrames and handle empty results gracefully.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd

from src.data.init_db import get_connection

# ---------------------------------------------------------------------------
# Valid dimension values
# ---------------------------------------------------------------------------

_VALID_EVENT_TYPES = frozenset({
    "campaign_launch", "review_cycle", "compliance_deadline",
    "exec_briefing", "budget_review", "team_sync", "other",
})

_VALID_EVENT_STATUSES = frozenset({
    "scheduled", "in_progress", "completed", "cancelled",
})

_VALID_APPROVAL_STATUSES = frozenset({
    "pending", "in_review", "approved", "rejected", "escalated",
})

_VALID_APPROVAL_CATEGORIES = frozenset({
    "creative", "budget_change", "compliance",
    "vendor_contract", "campaign_brief", "other",
})

_VALID_SYSTEM_STATUSES = frozenset({
    "healthy", "degraded", "down", "maintenance", "unknown",
})

_VALID_INTEL_CATEGORIES = frozenset({
    "rate_change", "product_launch", "marketing_campaign",
    "branch_expansion", "partnership", "regulatory", "other",
})

_VALID_INTEL_IMPACTS = frozenset({"low", "medium", "high", "critical"})

_VALID_TEAM_FUNCTIONS = frozenset({
    "brand", "performance_media", "seo_content", "analytics",
    "creative", "product_marketing", "ops", "other",
})


# ---------------------------------------------------------------------------
# 1. load_calendar_events
# ---------------------------------------------------------------------------


def load_calendar_events(
    month: Optional[str] = None,
    status: Optional[str] = None,
    event_type: Optional[str] = None,
) -> pd.DataFrame:
    """Load calendar events, optionally filtered by month, status, or event_type.

    Args:
        month: ISO month string ``YYYY-MM`` to filter by (matches start_dt).
               If None, returns all events ordered by start_dt ascending.
        status: One of ``scheduled | in_progress | completed | cancelled``.
        event_type: One of the CalendarEvent event_type enum values.

    Returns:
        DataFrame with columns:
            id, title, event_type, status, start_dt (datetime),
            end_dt (datetime), owner, attendees, description,
            related_campaign_id, created_at
    """
    if status is not None and status not in _VALID_EVENT_STATUSES:
        raise ValueError(f"Invalid status {status!r}. Must be one of {sorted(_VALID_EVENT_STATUSES)}")
    if event_type is not None and event_type not in _VALID_EVENT_TYPES:
        raise ValueError(f"Invalid event_type {event_type!r}. Must be one of {sorted(_VALID_EVENT_TYPES)}")

    conditions: list[str] = []
    if month is not None:
        # month filter: strftime on start_dt
        conditions.append(f"strftime(start_dt, '%Y-%m') = '{month}'")
    if status is not None:
        conditions.append(f"status = '{status}'")
    if event_type is not None:
        conditions.append(f"event_type = '{event_type}'")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
        SELECT
            id,
            title,
            event_type,
            status,
            start_dt,
            end_dt,
            owner,
            attendees,
            description,
            related_campaign_id,
            created_at
        FROM calendar_events
        {where}
        ORDER BY start_dt ASC
    """

    conn = get_connection()
    try:
        df = conn.execute(sql).df()
    finally:
        conn.close()

    # Ensure datetime dtype
    for col in ("start_dt", "end_dt", "created_at"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])

    return df


# ---------------------------------------------------------------------------
# 2. load_approval_queue
# ---------------------------------------------------------------------------


def load_approval_queue(
    status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
) -> pd.DataFrame:
    """Load approval queue items, optionally filtered by status, category, or priority.

    Args:
        status: One of ``pending | in_review | approved | rejected | escalated``.
                If None, returns all items.
        category: One of the ApprovalCategory enum values.
        priority: One of ``low | medium | high | urgent``.

    Returns:
        DataFrame with columns:
            id, title, category, status, priority, requestor, approver,
            due_date (datetime), resolved_at (datetime), budget_impact (float),
            notes, artifact_url, created_at
        Ordered by priority (urgent→low) then due_date ascending.
    """
    if status is not None and status not in _VALID_APPROVAL_STATUSES:
        raise ValueError(f"Invalid status {status!r}. Must be one of {sorted(_VALID_APPROVAL_STATUSES)}")
    if category is not None and category not in _VALID_APPROVAL_CATEGORIES:
        raise ValueError(f"Invalid category {category!r}. Must be one of {sorted(_VALID_APPROVAL_CATEGORIES)}")

    conditions: list[str] = []
    if status is not None:
        conditions.append(f"status = '{status}'")
    if category is not None:
        conditions.append(f"category = '{category}'")
    if priority is not None:
        conditions.append(f"priority = '{priority}'")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
        SELECT
            id,
            title,
            category,
            status,
            priority,
            requestor,
            approver,
            due_date,
            resolved_at,
            CAST(budget_impact AS DOUBLE) AS budget_impact,
            notes,
            artifact_url,
            created_at
        FROM approval_items
        {where}
        ORDER BY
            CASE priority
                WHEN 'urgent' THEN 1
                WHEN 'high'   THEN 2
                WHEN 'medium' THEN 3
                WHEN 'low'    THEN 4
                ELSE 5
            END,
            due_date ASC NULLS LAST
    """

    conn = get_connection()
    try:
        df = conn.execute(sql).df()
    finally:
        conn.close()

    for col in ("due_date", "resolved_at", "created_at"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])

    return df


# ---------------------------------------------------------------------------
# 3. load_system_health
# ---------------------------------------------------------------------------


def load_system_health(
    status: Optional[str] = None,
    category: Optional[str] = None,
) -> pd.DataFrame:
    """Load system health checks.

    Args:
        status: Filter to ``healthy | degraded | down | maintenance | unknown``.
        category: Filter to a SystemCategory value.

    Returns:
        DataFrame with columns:
            id, system_name, category, status, checked_at (datetime),
            response_time_ms (int/NA), uptime_pct (float/NA), error_message,
            owner_team, last_incident_at (datetime/NA), created_at
        Ordered by status severity (down → degraded → maintenance → healthy),
        then system_name.
    """
    if status is not None and status not in _VALID_SYSTEM_STATUSES:
        raise ValueError(f"Invalid status {status!r}. Must be one of {sorted(_VALID_SYSTEM_STATUSES)}")

    conditions: list[str] = []
    if status is not None:
        conditions.append(f"status = '{status}'")
    if category is not None:
        conditions.append(f"category = '{category}'")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
        SELECT
            id,
            system_name,
            category,
            status,
            checked_at,
            response_time_ms,
            CAST(uptime_pct AS DOUBLE) AS uptime_pct,
            error_message,
            owner_team,
            last_incident_at,
            created_at
        FROM system_health_checks
        {where}
        ORDER BY
            CASE status
                WHEN 'down'        THEN 1
                WHEN 'degraded'    THEN 2
                WHEN 'maintenance' THEN 3
                WHEN 'unknown'     THEN 4
                WHEN 'healthy'     THEN 5
                ELSE 6
            END,
            system_name ASC
    """

    conn = get_connection()
    try:
        df = conn.execute(sql).df()
    finally:
        conn.close()

    for col in ("checked_at", "last_incident_at", "created_at"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])

    return df


# ---------------------------------------------------------------------------
# 4. load_competitive_feed
# ---------------------------------------------------------------------------


def load_competitive_feed(
    category: Optional[str] = None,
    impact: Optional[str] = None,
    competitor: Optional[str] = None,
    unactioned_only: bool = False,
) -> pd.DataFrame:
    """Load competitive intelligence feed items.

    Args:
        category: Filter to an IntelCategory value (e.g. ``rate_change``).
        impact: Filter to ``low | medium | high | critical``.
        competitor: Filter by competitor_name (case-sensitive).
        unactioned_only: If True, returns only rows where is_actioned = FALSE.

    Returns:
        DataFrame with columns:
            id, competitor_name, category, impact, headline, detail,
            source_url, observed_date (date), product_affected, rate_delta_bps (int/NA),
            response_recommended, is_actioned (bool), created_at
        Ordered by impact severity (critical→low) then observed_date descending.
    """
    if category is not None and category not in _VALID_INTEL_CATEGORIES:
        raise ValueError(f"Invalid category {category!r}. Must be one of {sorted(_VALID_INTEL_CATEGORIES)}")
    if impact is not None and impact not in _VALID_INTEL_IMPACTS:
        raise ValueError(f"Invalid impact {impact!r}. Must be one of {sorted(_VALID_INTEL_IMPACTS)}")

    conditions: list[str] = []
    if category is not None:
        conditions.append(f"category = '{category}'")
    if impact is not None:
        conditions.append(f"impact = '{impact}'")
    if competitor is not None:
        # Use parameterized-style escaping — competitor names are trusted seed data
        safe_competitor = competitor.replace("'", "''")
        conditions.append(f"competitor_name = '{safe_competitor}'")
    if unactioned_only:
        conditions.append("is_actioned = FALSE")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
        SELECT
            id,
            competitor_name,
            category,
            impact,
            headline,
            detail,
            source_url,
            observed_date,
            product_affected,
            rate_delta_bps,
            response_recommended,
            is_actioned,
            created_at
        FROM competitive_intel_items
        {where}
        ORDER BY
            CASE impact
                WHEN 'critical' THEN 1
                WHEN 'high'     THEN 2
                WHEN 'medium'   THEN 3
                WHEN 'low'      THEN 4
                ELSE 5
            END,
            observed_date DESC
    """

    conn = get_connection()
    try:
        df = conn.execute(sql).df()
    finally:
        conn.close()

    if "observed_date" in df.columns:
        df["observed_date"] = pd.to_datetime(df["observed_date"]).dt.date
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"])

    return df


# ---------------------------------------------------------------------------
# 5. load_team_capacity
# ---------------------------------------------------------------------------


def load_team_capacity(
    period: Optional[str] = None,
    function: Optional[str] = None,
) -> pd.DataFrame:
    """Load team capacity snapshots.

    Args:
        period: ISO month ``YYYY-MM`` to filter. If None, returns all periods.
        function: Filter to a TeamFunction value (e.g. ``analytics``).

    Returns:
        DataFrame with columns:
            id, team_name, function, period, headcount_total, headcount_fte,
            open_reqs, utilization_pct (float), capacity_available_hrs (int/NA),
            notes, created_at
        Ordered by period descending, then utilization_pct descending.
    """
    if function is not None and function not in _VALID_TEAM_FUNCTIONS:
        raise ValueError(f"Invalid function {function!r}. Must be one of {sorted(_VALID_TEAM_FUNCTIONS)}")

    conditions: list[str] = []
    if period is not None:
        conditions.append(f"period = '{period}'")
    if function is not None:
        conditions.append(f"function = '{function}'")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
        SELECT
            id,
            team_name,
            function,
            period,
            headcount_total,
            headcount_fte,
            open_reqs,
            CAST(utilization_pct AS DOUBLE) AS utilization_pct,
            capacity_available_hrs,
            notes,
            created_at
        FROM team_capacity
        {where}
        ORDER BY period DESC, utilization_pct DESC
    """

    conn = get_connection()
    try:
        df = conn.execute(sql).df()
    finally:
        conn.close()

    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"])

    return df


# ---------------------------------------------------------------------------
# 6. approve_item
# ---------------------------------------------------------------------------


def approve_item(item_id: str, approver: Optional[str] = None) -> bool:
    """Approve a pending or in-review approval item.

    Sets status → 'approved', resolved_at → now(), updated_at → now().

    Args:
        item_id: UUID string of the ApprovalItem to approve.
        approver: Name of the approver to record (optional, overwrites existing).

    Returns:
        True if exactly one row was updated, False if item not found or
        already in a terminal state (approved/rejected).
    """
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    approver_clause = f", approver = '{approver.replace(chr(39), chr(39)*2)}'" if approver else ""

    sql = f"""
        UPDATE approval_items
        SET
            status      = 'approved',
            resolved_at = TIMESTAMP '{now_str}',
            updated_at  = TIMESTAMP '{now_str}'
            {approver_clause}
        WHERE id = '{item_id}'
          AND status IN ('pending', 'in_review', 'escalated')
        RETURNING id
    """

    conn = get_connection()
    try:
        result = conn.execute(sql).fetchall()
        conn.commit()
    finally:
        conn.close()

    return len(result) == 1


# ---------------------------------------------------------------------------
# 7. reject_item
# ---------------------------------------------------------------------------


def reject_item(item_id: str, reason: Optional[str] = None, approver: Optional[str] = None) -> bool:
    """Reject a pending or in-review approval item.

    Sets status → 'rejected', notes → reason (if provided),
    resolved_at → now(), updated_at → now().

    Args:
        item_id: UUID string of the ApprovalItem to reject.
        reason: Rejection reason string stored in the notes field.
        approver: Name of the approver recording the rejection (optional).

    Returns:
        True if exactly one row was updated, False if item not found or
        already in a terminal state (approved/rejected).
    """
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    notes_clause = ""
    if reason is not None:
        safe_reason = reason.replace("'", "''")
        notes_clause = f", notes = '{safe_reason}'"

    approver_clause = ""
    if approver is not None:
        safe_approver = approver.replace("'", "''")
        approver_clause = f", approver = '{safe_approver}'"

    sql = f"""
        UPDATE approval_items
        SET
            status      = 'rejected',
            resolved_at = TIMESTAMP '{now_str}',
            updated_at  = TIMESTAMP '{now_str}'
            {notes_clause}
            {approver_clause}
        WHERE id = '{item_id}'
          AND status IN ('pending', 'in_review', 'escalated')
        RETURNING id
    """

    conn = get_connection()
    try:
        result = conn.execute(sql).fetchall()
        conn.commit()
    finally:
        conn.close()

    return len(result) == 1
