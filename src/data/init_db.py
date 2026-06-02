"""DuckDB initialization — creates stub tables if they don't exist.

Idempotent: safe to run multiple times; uses CREATE TABLE IF NOT EXISTS.
Dev mode: connects to a local .duckdb file (DB_PATH from settings).
Prod mode: connects to PostgreSQL via DB_URL.
"""

import duckdb
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from src.config.settings import DB_PATH, DB_URL, is_dev_mode

# DDL for each stub table
_DDL = [
    """
    CREATE TABLE IF NOT EXISTS kpi_metrics (
        id          INTEGER PRIMARY KEY,
        metric_name VARCHAR NOT NULL,
        metric_value DOUBLE,
        period_start DATE,
        period_end   DATE,
        channel      VARCHAR,
        segment      VARCHAR,
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS campaigns (
        id           INTEGER PRIMARY KEY,
        name         VARCHAR NOT NULL,
        channel      VARCHAR,
        status       VARCHAR DEFAULT 'draft',
        budget       DOUBLE,
        spend        DOUBLE DEFAULT 0,
        impressions  BIGINT DEFAULT 0,
        clicks       BIGINT DEFAULT 0,
        conversions  BIGINT DEFAULT 0,
        start_date   DATE,
        end_date     DATE,
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS competitors (
        id             INTEGER PRIMARY KEY,
        name           VARCHAR NOT NULL,
        market_segment VARCHAR,
        website        VARCHAR,
        ad_spend_est   DOUBLE,
        share_of_voice DOUBLE,
        sentiment_score DOUBLE,
        last_scraped_at TIMESTAMP,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS leads (
        id            INTEGER PRIMARY KEY,
        source        VARCHAR,
        campaign_id   INTEGER,
        status        VARCHAR DEFAULT 'new',
        score         INTEGER DEFAULT 0,
        first_name    VARCHAR,
        last_name     VARCHAR,
        email         VARCHAR,
        company       VARCHAR,
        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        converted_at  TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS scenarios (
        id          INTEGER PRIMARY KEY,
        name        VARCHAR NOT NULL UNIQUE,
        payload     JSON    NOT NULL,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS directives (
        id            INTEGER PRIMARY KEY,
        scenario_name VARCHAR NOT NULL,
        payload       JSON    NOT NULL,
        note          VARCHAR DEFAULT '',
        submitted_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
]


@st.cache_resource
def get_engine() -> Engine:
    """Return a SQLAlchemy engine, cached across Streamlit reruns."""
    if is_dev_mode():
        return create_engine(f"duckdb:///{DB_PATH}")
    return create_engine(DB_URL)


def get_connection() -> duckdb.DuckDBPyConnection:
    """Return a DuckDB connection (file-based in dev, in-memory proxy in prod)."""
    if is_dev_mode():
        return duckdb.connect(DB_PATH, read_only=True)
    # In prod the app connects to PostgreSQL; DuckDB is used for local analytics
    # only. Return an in-memory connection so this module is still importable.
    return duckdb.connect(":memory:")


def init_db() -> None:
    """Create all stub tables. Idempotent — safe to call on every app startup."""
    conn = get_connection()
    try:
        for ddl in _DDL:
            conn.execute(ddl)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print("DB initialized.")
