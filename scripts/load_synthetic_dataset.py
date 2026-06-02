#!/usr/bin/env python3
"""Load the full-funnel synthetic banking dataset into Apex DuckDB.

Maps 14 CSV files from the second-brain synthetic dataset into Apex tables:
  - Existing tables: campaigns, campaign_performance, budgets
  - New tables: brand_media_daily, brand_reach_frequency, aeo_visibility_daily,
    google_branded_uoi, seo_visits_daily, sem_daily, social_paid_daily,
    display_retargeting_daily, email_daily, direct_mail_daily, site_sessions,
    application_events, customer_conversions, funnel_summary_daily

Follows the existing Apex seed pattern: DuckDB direct connect, DataFrame register,
INSERT via SQL. Idempotent — safe to run multiple times (DROP + CREATE).

Usage:
    python -m scripts.load_synthetic_dataset
    # or from Apex root:
    python scripts/load_synthetic_dataset.py
"""

from __future__ import annotations

import os
import sys
import time
import uuid
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

# ---------------------------------------------------------------------------
# Path bootstrap — ensure Apex src/ is importable
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
APEX_ROOT = SCRIPT_DIR.parent
if str(APEX_ROOT) not in sys.path:
    sys.path.insert(0, str(APEX_ROOT))

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CSV_DIR = Path("/sessions/festive-beautiful-johnson/mnt/second-brain/output/synthetic-banking-dataset")
DB_PATH = APEX_ROOT / os.environ.get("APEX_DB_NAME", "apex_clean.duckdb")

# CSV → Apex table mapping
CSV_TABLE_MAP = {
    "brand_media_daily.csv":          "brand_media_daily",
    "brand_reach_frequency.csv":      "brand_reach_frequency",
    "aeo_visibility_daily.csv":       "aeo_visibility_daily",
    "google_branded_uoi.csv":         "google_branded_uoi",
    "seo_visits_daily.csv":           "seo_visits_daily",
    "sem_daily.csv":                  "sem_daily",
    "social_paid_daily.csv":          "social_paid_daily",
    "display_retargeting_daily.csv":  "display_retargeting_daily",
    "email_daily.csv":                "email_daily",
    "direct_mail_daily.csv":          "direct_mail_daily",
    "site_sessions.csv":             "site_sessions",
    "application_events.csv":         "application_events",
    "customer_conversions.csv":       "customer_conversions",
    "funnel_summary_daily.csv":       "funnel_summary_daily",
}

# ---------------------------------------------------------------------------
# DDL for each new table — typed for DuckDB
# ---------------------------------------------------------------------------
TABLE_DDL = {

    "brand_media_daily": """
    CREATE TABLE IF NOT EXISTS brand_media_daily (
        date            DATE NOT NULL,
        dma_id          VARCHAR NOT NULL,
        dma_name        VARCHAR NOT NULL,
        channel_id      VARCHAR NOT NULL,
        channel_name    VARCHAR NOT NULL,
        audience_id     VARCHAR NOT NULL,
        audience_name   VARCHAR NOT NULL,
        creative_id     VARCHAR NOT NULL,
        creative_name   VARCHAR NOT NULL,
        ad_id           VARCHAR NOT NULL,
        product         VARCHAR NOT NULL,
        impressions     BIGINT NOT NULL,
        interactions    BIGINT NOT NULL,
        spend           DECIMAL(18,4) NOT NULL
    )
    """,

    "brand_reach_frequency": """
    CREATE TABLE IF NOT EXISTS brand_reach_frequency (
        date                    DATE NOT NULL,
        dma_id                  VARCHAR NOT NULL,
        dma_name                VARCHAR NOT NULL,
        hh_universe             INTEGER NOT NULL,
        daily_impressions       BIGINT NOT NULL,
        daily_reach             INTEGER NOT NULL,
        daily_reach_pct         DECIMAL(8,4) NOT NULL,
        daily_frequency         DECIMAL(8,4) NOT NULL,
        rolling_7d_reach        INTEGER NOT NULL,
        rolling_7d_frequency    DECIMAL(8,4) NOT NULL,
        rolling_30d_reach       INTEGER NOT NULL,
        rolling_30d_frequency   DECIMAL(8,4) NOT NULL
    )
    """,

    "aeo_visibility_daily": """
    CREATE TABLE IF NOT EXISTS aeo_visibility_daily (
        date                          DATE NOT NULL,
        keyword_cluster_id            VARCHAR NOT NULL,
        keyword_cluster               VARCHAR NOT NULL,
        visibility_score              DECIMAL(8,4) NOT NULL,
        estimated_ai_impressions      INTEGER NOT NULL,
        citation_rate                 DECIMAL(8,4) NOT NULL,
        estimated_ai_referral_clicks  INTEGER NOT NULL
    )
    """,

    "google_branded_uoi": """
    CREATE TABLE IF NOT EXISTS google_branded_uoi (
        date                        DATE NOT NULL,
        dma_id                      VARCHAR NOT NULL,
        dma_name                    VARCHAR NOT NULL,
        branded_searches            INTEGER NOT NULL,
        branded_uoi                 INTEGER NOT NULL,
        branded_clicks              INTEGER NOT NULL,
        branded_ctr                 DECIMAL(8,4) NOT NULL,
        organic_baseline_searches   INTEGER NOT NULL,
        media_lift_searches         INTEGER NOT NULL,
        media_lift_pct              DECIMAL(8,4) NOT NULL,
        direct_entry_visits         INTEGER NOT NULL,
        brand_impression_input      BIGINT NOT NULL
    )
    """,

    "seo_visits_daily": """
    CREATE TABLE IF NOT EXISTS seo_visits_daily (
        date                            DATE NOT NULL,
        dma_id                          VARCHAR NOT NULL,
        dma_name                        VARCHAR NOT NULL,
        brand_seo_visits                INTEGER NOT NULL,
        non_brand_seo_visits            INTEGER NOT NULL,
        total_seo_visits                INTEGER NOT NULL,
        brand_seo_bounce_rate           DECIMAL(8,4) NOT NULL,
        non_brand_seo_bounce_rate       DECIMAL(8,4) NOT NULL,
        brand_seo_pages_per_session     DECIMAL(8,4) NOT NULL,
        non_brand_seo_pages_per_session DECIMAL(8,4) NOT NULL
    )
    """,

    "sem_daily": """
    CREATE TABLE IF NOT EXISTS sem_daily (
        date                DATE NOT NULL,
        dma_id              VARCHAR NOT NULL,
        dma_name            VARCHAR NOT NULL,
        campaign_id         VARCHAR NOT NULL,
        campaign_name       VARCHAR NOT NULL,
        campaign_type       VARCHAR NOT NULL,
        search_engine       VARCHAR NOT NULL DEFAULT 'google',
        product             VARCHAR NOT NULL,
        impressions         BIGINT NOT NULL,
        clicks              INTEGER NOT NULL,
        ctr                 DECIMAL(10,6) NOT NULL,
        avg_cpc             DECIMAL(10,4) NOT NULL,
        spend               DECIMAL(18,4) NOT NULL,
        impression_share    DECIMAL(8,4) NOT NULL,
        avg_position        DECIMAL(6,2) NOT NULL,
        quality_score       DECIMAL(4,1) NOT NULL,
        conversions         INTEGER NOT NULL
    )
    """,

    "social_paid_daily": """
    CREATE TABLE IF NOT EXISTS social_paid_daily (
        date            DATE NOT NULL,
        dma_id          VARCHAR NOT NULL,
        dma_name        VARCHAR NOT NULL,
        campaign_id     VARCHAR NOT NULL,
        campaign_name   VARCHAR NOT NULL,
        platform        VARCHAR NOT NULL,
        objective       VARCHAR NOT NULL,
        audience_id     VARCHAR NOT NULL,
        audience_name   VARCHAR NOT NULL,
        creative_id     VARCHAR NOT NULL,
        creative_name   VARCHAR NOT NULL,
        ad_id           VARCHAR NOT NULL,
        product         VARCHAR NOT NULL,
        impressions     BIGINT NOT NULL,
        clicks          INTEGER NOT NULL,
        ctr             DECIMAL(10,6) NOT NULL,
        spend           DECIMAL(18,4) NOT NULL,
        cpm             DECIMAL(10,4) NOT NULL,
        likes           INTEGER NOT NULL,
        shares          INTEGER NOT NULL,
        comments        INTEGER NOT NULL,
        saves           INTEGER NOT NULL,
        video_views     INTEGER NOT NULL
    )
    """,

    "display_retargeting_daily": """
    CREATE TABLE IF NOT EXISTS display_retargeting_daily (
        date                        DATE NOT NULL,
        dma_id                      VARCHAR NOT NULL,
        dma_name                    VARCHAR NOT NULL,
        campaign_id                 VARCHAR NOT NULL,
        campaign_name               VARCHAR NOT NULL,
        campaign_type               VARCHAR NOT NULL,
        audience_id                 VARCHAR NOT NULL,
        audience_name               VARCHAR NOT NULL,
        creative_id                 VARCHAR NOT NULL,
        creative_name               VARCHAR NOT NULL,
        ad_id                       VARCHAR NOT NULL,
        product                     VARCHAR NOT NULL,
        impressions                 BIGINT NOT NULL,
        clicks                      INTEGER NOT NULL,
        ctr                         DECIMAL(10,6) NOT NULL,
        spend                       DECIMAL(18,4) NOT NULL,
        viewthrough_conversions     INTEGER NOT NULL
    )
    """,

    "email_daily": """
    CREATE TABLE IF NOT EXISTS email_daily (
        date            DATE NOT NULL,
        dma_id          VARCHAR NOT NULL,
        dma_name        VARCHAR NOT NULL,
        campaign_id     VARCHAR NOT NULL,
        campaign_name   VARCHAR NOT NULL,
        campaign_type   VARCHAR NOT NULL,
        product         VARCHAR NOT NULL,
        ad_id           VARCHAR NOT NULL,
        sends           INTEGER NOT NULL,
        delivered       INTEGER NOT NULL,
        opens           INTEGER NOT NULL,
        open_rate       DECIMAL(8,4) NOT NULL,
        clicks          INTEGER NOT NULL,
        click_rate      DECIMAL(8,4) NOT NULL,
        unsubscribes    INTEGER NOT NULL,
        bounces         INTEGER NOT NULL
    )
    """,

    "direct_mail_daily": """
    CREATE TABLE IF NOT EXISTS direct_mail_daily (
        date                    DATE NOT NULL,
        dma_id                  VARCHAR NOT NULL,
        dma_name                VARCHAR NOT NULL,
        campaign_id             VARCHAR NOT NULL,
        campaign_name           VARCHAR NOT NULL,
        product                 VARCHAR NOT NULL,
        ad_id                   VARCHAR NOT NULL,
        pieces_mailed           INTEGER NOT NULL,
        total_responses         INTEGER NOT NULL,
        qr_code_scans           INTEGER NOT NULL,
        phone_responses         INTEGER NOT NULL,
        branch_visit_responses  INTEGER NOT NULL,
        cost                    DECIMAL(18,4) NOT NULL,
        cost_per_response       DECIMAL(10,4) NOT NULL,
        response_rate           DECIMAL(10,6) NOT NULL
    )
    """,

    "site_sessions": """
    CREATE TABLE IF NOT EXISTS site_sessions (
        date                    DATE NOT NULL,
        session_id              VARCHAR NOT NULL,
        anonymous_id            VARCHAR NOT NULL,
        click_id                VARCHAR,
        ad_id                   VARCHAR,
        dma_id                  VARCHAR NOT NULL,
        dma_name                VARCHAR NOT NULL,
        channel                 VARCHAR NOT NULL,
        channel_detail          VARCHAR NOT NULL,
        campaign_id             VARCHAR,
        audience_id             VARCHAR,
        product_interest        VARCHAR NOT NULL,
        landing_page            VARCHAR NOT NULL,
        pages_viewed            INTEGER NOT NULL,
        session_duration_sec    INTEGER NOT NULL,
        bounced                 TINYINT NOT NULL,
        viewed_product_page     TINYINT NOT NULL,
        started_application     TINYINT NOT NULL,
        device                  VARCHAR NOT NULL,
        new_visitor             TINYINT NOT NULL
    )
    """,

    "application_events": """
    CREATE TABLE IF NOT EXISTS application_events (
        date                        DATE NOT NULL,
        application_id              VARCHAR NOT NULL,
        user_id                     VARCHAR NOT NULL,
        anonymous_id                VARCHAR NOT NULL,
        click_id                    VARCHAR,
        ad_id                       VARCHAR,
        session_id                  VARCHAR NOT NULL,
        dma_id                      VARCHAR NOT NULL,
        dma_name                    VARCHAR NOT NULL,
        channel                     VARCHAR NOT NULL,
        channel_detail              VARCHAR NOT NULL,
        campaign_id                 VARCHAR,
        audience_id                 VARCHAR,
        product_id                  VARCHAR NOT NULL,
        product_name                VARCHAR NOT NULL,
        application_status          VARCHAR NOT NULL,
        reached_identity_verify     TINYINT NOT NULL,
        reached_submit              TINYINT NOT NULL,
        reached_decision            TINYINT NOT NULL,
        approved                    TINYINT NOT NULL,
        time_to_complete_min        INTEGER NOT NULL,
        device                      VARCHAR NOT NULL
    )
    """,

    "customer_conversions": """
    CREATE TABLE IF NOT EXISTS customer_conversions (
        application_date    DATE NOT NULL,
        funded_date         DATE NOT NULL,
        customer_id         VARCHAR NOT NULL,
        user_id             VARCHAR NOT NULL,
        anonymous_id        VARCHAR NOT NULL,
        click_id            VARCHAR,
        ad_id               VARCHAR,
        application_id      VARCHAR NOT NULL,
        session_id          VARCHAR NOT NULL,
        dma_id              VARCHAR NOT NULL,
        dma_name            VARCHAR NOT NULL,
        channel             VARCHAR NOT NULL,
        channel_detail      VARCHAR NOT NULL,
        campaign_id         VARCHAR,
        audience_id         VARCHAR,
        product_id          VARCHAR NOT NULL,
        product_name        VARCHAR NOT NULL,
        initial_deposit     INTEGER NOT NULL,
        funding_lag_days    INTEGER NOT NULL,
        device              VARCHAR NOT NULL,
        is_new_to_bank      TINYINT NOT NULL
    )
    """,

    "funnel_summary_daily": """
    CREATE TABLE IF NOT EXISTS funnel_summary_daily (
        date                    DATE NOT NULL,
        dma_id                  VARCHAR NOT NULL,
        dma_name                VARCHAR NOT NULL,
        brand_impressions       BIGINT NOT NULL,
        brand_interactions      BIGINT NOT NULL,
        brand_spend             DECIMAL(18,4) NOT NULL,
        sem_impressions         BIGINT NOT NULL,
        sem_clicks              INTEGER NOT NULL,
        sem_spend               DECIMAL(18,4) NOT NULL,
        social_impressions      BIGINT NOT NULL,
        social_clicks           INTEGER NOT NULL,
        social_spend            DECIMAL(18,4) NOT NULL,
        display_impressions     BIGINT NOT NULL,
        display_clicks          INTEGER NOT NULL,
        display_spend           DECIMAL(18,4) NOT NULL,
        site_sessions           INTEGER NOT NULL,
        site_bounce_rate        DECIMAL(8,4) NOT NULL,
        product_page_views      INTEGER NOT NULL,
        applications_started    INTEGER NOT NULL,
        applications_submitted  INTEGER NOT NULL,
        applications_approved   INTEGER NOT NULL,
        accounts_funded         INTEGER NOT NULL,
        total_initial_deposits  DECIMAL(18,4) NOT NULL
    )
    """,
}


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_table(conn: duckdb.DuckDBPyConnection, csv_name: str, table_name: str,
               verbose: bool = True) -> int:
    """Load one CSV into a DuckDB table. Returns row count."""
    csv_path = CSV_DIR / csv_name
    if not csv_path.exists():
        print(f"  [SKIP] {csv_name} not found")
        return 0

    t0 = time.time()

    # Drop and recreate
    conn.execute(f"DROP TABLE IF EXISTS {table_name}")

    if table_name in TABLE_DDL:
        conn.execute(TABLE_DDL[table_name])
    else:
        raise ValueError(f"No DDL defined for {table_name}")

    # For large files (site_sessions), use DuckDB's native CSV reader for speed
    file_size_mb = csv_path.stat().st_size / (1024 * 1024)

    if file_size_mb > 50:
        # Direct CSV read — much faster for large files
        conn.execute(f"""
            INSERT INTO {table_name}
            SELECT * FROM read_csv_auto('{csv_path}',
                         header=true,
                         nullstr='',
                         ignore_errors=true)
        """)
        row_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    else:
        # Small file — read via pandas for type control
        df = pd.read_csv(csv_path, keep_default_na=False)
        # Convert empty strings to None for nullable columns
        df = df.replace('', None)
        conn.register("_tmp_df", df)
        cols = ", ".join(df.columns)
        conn.execute(f"INSERT INTO {table_name} SELECT {cols} FROM _tmp_df")
        row_count = len(df)
        conn.unregister("_tmp_df")

    elapsed = time.time() - t0
    if verbose:
        print(f"  [OK] {table_name:35s} {row_count:>12,} rows  ({elapsed:.1f}s, {file_size_mb:.1f} MB)")
    return row_count


def create_indexes(conn: duckdb.DuckDBPyConnection, verbose: bool = True):
    """Create indexes for common query patterns."""
    indexes = [
        ("idx_brand_media_date_dma",     "brand_media_daily",          "date, dma_id"),
        ("idx_brand_media_channel",      "brand_media_daily",          "channel_id"),
        ("idx_brand_rf_date_dma",        "brand_reach_frequency",      "date, dma_id"),
        ("idx_aeo_date",                 "aeo_visibility_daily",       "date"),
        ("idx_uoi_date_dma",             "google_branded_uoi",         "date, dma_id"),
        ("idx_seo_date_dma",             "seo_visits_daily",           "date, dma_id"),
        ("idx_sem_date_dma",             "sem_daily",                  "date, dma_id"),
        ("idx_sem_campaign",             "sem_daily",                  "campaign_id"),
        ("idx_sem_engine",               "sem_daily",                  "search_engine"),
        ("idx_social_date_dma",          "social_paid_daily",          "date, dma_id"),
        ("idx_social_platform",          "social_paid_daily",          "platform"),
        ("idx_display_date_dma",         "display_retargeting_daily",  "date, dma_id"),
        ("idx_email_date",               "email_daily",                "date"),
        ("idx_dm_date_dma",              "direct_mail_daily",          "date, dma_id"),
        ("idx_sessions_date_dma",        "site_sessions",              "date, dma_id"),
        ("idx_sessions_channel",         "site_sessions",              "channel"),
        ("idx_sessions_anon",            "site_sessions",              "anonymous_id"),
        ("idx_sessions_click",           "site_sessions",              "click_id"),
        ("idx_apps_date_dma",            "application_events",         "date, dma_id"),
        ("idx_apps_channel",             "application_events",         "channel"),
        ("idx_apps_user",                "application_events",         "user_id"),
        ("idx_apps_status",              "application_events",         "application_status"),
        ("idx_cust_funded_date",         "customer_conversions",       "funded_date"),
        ("idx_cust_channel",             "customer_conversions",       "channel"),
        ("idx_cust_customer",            "customer_conversions",       "customer_id"),
        ("idx_cust_user",                "customer_conversions",       "user_id"),
        ("idx_funnel_date_dma",          "funnel_summary_daily",       "date, dma_id"),
    ]
    if verbose:
        print("\nCreating indexes...")
    for idx_name, table, cols in indexes:
        conn.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({cols})")
    if verbose:
        print(f"  [OK] {len(indexes)} indexes created")


def create_views(conn: duckdb.DuckDBPyConnection, verbose: bool = True):
    """Create analytical views for common Apex queries."""

    views = {
        # Monthly funnel rollup
        "v_funnel_monthly": """
        CREATE OR REPLACE VIEW v_funnel_monthly AS
        SELECT
            DATE_TRUNC('month', date) AS month,
            dma_id, dma_name,
            SUM(brand_impressions) AS brand_impressions,
            SUM(brand_spend) AS brand_spend,
            SUM(sem_clicks) AS sem_clicks,
            SUM(sem_spend) AS sem_spend,
            SUM(social_clicks) AS social_clicks,
            SUM(social_spend) AS social_spend,
            SUM(display_clicks) AS display_clicks,
            SUM(display_spend) AS display_spend,
            SUM(site_sessions) AS site_sessions,
            SUM(product_page_views) AS product_page_views,
            SUM(applications_started) AS applications_started,
            SUM(applications_submitted) AS applications_submitted,
            SUM(applications_approved) AS applications_approved,
            SUM(accounts_funded) AS accounts_funded,
            SUM(total_initial_deposits) AS total_initial_deposits
        FROM funnel_summary_daily
        GROUP BY 1, 2, 3
        """,

        # Customer attribution — full chain with channel/campaign detail
        "v_customer_attribution": """
        CREATE OR REPLACE VIEW v_customer_attribution AS
        SELECT
            c.customer_id,
            c.funded_date,
            c.channel,
            c.channel_detail,
            c.campaign_id,
            c.audience_id,
            c.ad_id,
            c.product_id,
            c.product_name,
            c.dma_id,
            c.dma_name,
            c.initial_deposit,
            c.is_new_to_bank,
            c.device,
            c.funding_lag_days,
            CASE WHEN c.click_id IS NOT NULL AND c.click_id != ''
                 THEN 'paid' ELSE 'organic' END AS attribution_type
        FROM customer_conversions c
        """,

        # Channel performance summary
        "v_channel_performance": """
        CREATE OR REPLACE VIEW v_channel_performance AS
        SELECT
            DATE_TRUNC('month', a.date) AS month,
            a.channel,
            COUNT(DISTINCT a.application_id) AS applications,
            SUM(a.approved) AS approvals,
            COUNT(DISTINCT c.customer_id) AS funded_accounts,
            SUM(c.initial_deposit) AS total_deposits,
            ROUND(SUM(a.approved)::FLOAT / NULLIF(COUNT(a.application_id), 0), 4) AS approval_rate
        FROM application_events a
        LEFT JOIN customer_conversions c ON a.user_id = c.user_id
        GROUP BY 1, 2
        """,

        # Brand media lift — organic vs paid search by DMA
        "v_brand_search_lift": """
        CREATE OR REPLACE VIEW v_brand_search_lift AS
        SELECT
            date,
            dma_id, dma_name,
            organic_baseline_searches,
            media_lift_searches,
            media_lift_pct,
            branded_searches,
            branded_clicks,
            direct_entry_visits,
            brand_impression_input
        FROM google_branded_uoi
        """,

        # Application funnel by DOW
        "v_funnel_by_dow": """
        CREATE OR REPLACE VIEW v_funnel_by_dow AS
        SELECT
            DAYNAME(date) AS day_of_week,
            DAYOFWEEK(date) AS dow_num,
            AVG(site_sessions) AS avg_sessions,
            AVG(applications_started) AS avg_apps_started,
            AVG(applications_approved) AS avg_apps_approved,
            AVG(accounts_funded) AS avg_accounts_funded
        FROM funnel_summary_daily
        GROUP BY 1, 2
        ORDER BY 2
        """,
    }

    if verbose:
        print("\nCreating analytical views...")
    for name, sql in views.items():
        conn.execute(sql)
        if verbose:
            print(f"  [OK] {name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("LOADING SYNTHETIC DATASET INTO APEX DUCKDB")
    print("=" * 70)
    print(f"CSV source:  {CSV_DIR}")
    print(f"Database:    {DB_PATH}")
    print()

    # Build in /tmp to avoid WAL permission issues, then copy to final path
    import shutil
    tmp_db = Path("/tmp") / DB_PATH.name
    for f in [tmp_db, Path(str(tmp_db) + ".wal")]:
        if f.exists():
            f.unlink()
    conn = duckdb.connect(str(tmp_db))
    total_rows = 0
    t_start = time.time()

    try:
        # Load all tables (order: small → large for progress visibility)
        load_order = [
            "brand_reach_frequency.csv",
            "aeo_visibility_daily.csv",
            "google_branded_uoi.csv",
            "seo_visits_daily.csv",
            "funnel_summary_daily.csv",
            "direct_mail_daily.csv",
            "email_daily.csv",
            "sem_daily.csv",
            "social_paid_daily.csv",
            "display_retargeting_daily.csv",
            "application_events.csv",
            "customer_conversions.csv",
            "brand_media_daily.csv",
            "site_sessions.csv",       # biggest — last
        ]

        print("Loading tables:")
        for csv_name in load_order:
            table_name = CSV_TABLE_MAP[csv_name]
            rows = load_table(conn, csv_name, table_name)
            total_rows += rows

        conn.commit()

        # Create indexes
        create_indexes(conn)
        conn.commit()

        # Create views
        create_views(conn)
        conn.commit()

        elapsed = time.time() - t_start
        print()
        print("=" * 70)
        print(f"LOAD COMPLETE: {total_rows:,} total rows in {elapsed:.1f}s")
        print("=" * 70)

        # Quick verification
        print("\nVerification queries:")
        tables = conn.execute("SHOW TABLES").fetchall()
        print(f"  Tables in DB: {len(tables)}")
        for (t,) in sorted(tables):
            if t.startswith("alembic"):
                continue
            try:
                cnt = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                print(f"    {t:40s} {cnt:>12,}")
            except Exception:
                pass

        # Test the attribution view
        print("\n  v_customer_attribution sample:")
        sample = conn.execute("""
            SELECT channel, attribution_type, COUNT(*) as n,
                   ROUND(AVG(initial_deposit), 0) as avg_deposit
            FROM v_customer_attribution
            GROUP BY 1, 2
            ORDER BY n DESC
            LIMIT 10
        """).fetchdf()
        print(sample.to_string(index=False))

    finally:
        conn.close()

    # Copy built DB to final location
    shutil.copy2(str(tmp_db), str(DB_PATH))
    print(f"\nCopied DB to {DB_PATH}")
    # Clean up tmp
    for f in [tmp_db, Path(str(tmp_db) + ".wal")]:
        if f.exists():
            f.unlink()


if __name__ == "__main__":
    main()
