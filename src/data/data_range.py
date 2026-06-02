"""
data_range.py
-------------
Auto-detect the date range available in the synthetic dataset.
Cached at app startup so the filter bar can default to the actual data window
rather than using today's date (which may be outside the data range).

Also provides period-over-period date calculation utilities.
"""

from __future__ import annotations

import datetime
import os

import duckdb
import streamlit as st

from src.config.settings import is_dev_mode


def _get_db_path() -> str:
    """Return the path to the DuckDB database."""
    return os.environ.get("APEX_DB_PATH", "apex_clean.duckdb")


@st.cache_data(ttl=3600)
def get_data_date_range() -> tuple[datetime.date, datetime.date]:
    """
    Return (min_date, max_date) from the synthetic data.

    Queries funnel_summary_daily as the canonical date-range table.
    Falls back to (today - 90d, today) if the table doesn't exist.
    """
    try:
        con = duckdb.connect(_get_db_path(), read_only=True)
        try:
            row = con.execute(
                "SELECT MIN(date), MAX(date) FROM funnel_summary_daily"
            ).fetchone()
            if row and row[0] and row[1]:
                # Convert to datetime.date if needed
                min_d = row[0] if isinstance(row[0], datetime.date) else datetime.date.fromisoformat(str(row[0]))
                max_d = row[1] if isinstance(row[1], datetime.date) else datetime.date.fromisoformat(str(row[1]))
                return (min_d, max_d)
        finally:
            con.close()
    except Exception:
        pass

    # Fallback
    today = datetime.date.today()
    return (today - datetime.timedelta(days=365), today)


@st.cache_data(ttl=3600)
def get_available_dmas() -> list[str]:
    """Return the distinct DMA names present in the data."""
    try:
        con = duckdb.connect(_get_db_path(), read_only=True)
        try:
            rows = con.execute(
                "SELECT DISTINCT dma_name FROM funnel_summary_daily ORDER BY dma_name"
            ).fetchall()
            if rows:
                return [r[0] for r in rows]
        finally:
            con.close()
    except Exception:
        pass
    return []


@st.cache_data(ttl=3600)
def get_available_channels() -> list[str]:
    """Return the distinct channel names present in the data."""
    try:
        con = duckdb.connect(_get_db_path(), read_only=True)
        try:
            rows = con.execute(
                "SELECT DISTINCT channel FROM application_events ORDER BY channel"
            ).fetchall()
            if rows:
                return [r[0] for r in rows]
        finally:
            con.close()
    except Exception:
        pass
    return []


@st.cache_data(ttl=3600)
def get_available_products() -> list[str]:
    """Return the distinct product names present in the data."""
    try:
        con = duckdb.connect(_get_db_path(), read_only=True)
        try:
            rows = con.execute(
                "SELECT DISTINCT product_name FROM application_events ORDER BY product_name"
            ).fetchall()
            if rows:
                return [r[0] for r in rows]
        finally:
            con.close()
    except Exception:
        pass
    return []


def compute_prior_period(
    date_start: datetime.date,
    date_end: datetime.date,
) -> tuple[datetime.date, datetime.date]:
    """
    Compute the prior period of equal length ending the day before date_start.

    Example: if current period is Nov 1–Nov 30 (30 days),
    prior period is Oct 2–Oct 31 (30 days).

    Returns
    -------
    (prior_start, prior_end)
    """
    period_days = (date_end - date_start).days
    prior_end = date_start - datetime.timedelta(days=1)
    prior_start = prior_end - datetime.timedelta(days=period_days)
    return (prior_start, prior_end)
