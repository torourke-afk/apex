"""Seed: Alerts Data

Generates 30+ sample alerts for the Apex alerts module.

Schema (APE-9):
    alerts: id (UUID), title (str), severity (str: info/warning/critical),
            category (str: performance/budget/competitor/system),
            message (str), is_read (bool), resolved_at (datetime nullable),
            created_at, updated_at

Distributions:
  - Severity: 3-5 critical, 10-15 warning, 15-20 info
  - Categories: performance, budget, competitor, system
  - Mix of read/unread, some with resolved_at set
  - Timestamps spanning last 30 days

Idempotent: DELETE + INSERT on alerts table.

Run:
    python -m src.data.seeds.alerts
"""

from __future__ import annotations

import sys
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import List

import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema, Check
from faker import Faker

# ---------------------------------------------------------------------------
# Path bootstrap (allows running as script or module)
# ---------------------------------------------------------------------------
WORKSPACE = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if WORKSPACE not in sys.path:
    sys.path.insert(0, WORKSPACE)

from src.data.init_db import get_connection  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEED = 42
fake = Faker("en_US")
fake.seed_instance(SEED)

TODAY = datetime(2026, 5, 8, tzinfo=timezone.utc)
WINDOW_START = TODAY - timedelta(days=30)

SEVERITIES = ["info", "warning", "critical"]
CATEGORIES = ["performance", "budget", "competitor", "system"]

# ---------------------------------------------------------------------------
# Alert templates: (title, severity, category, message_template)
# Each entry is a concrete alert definition; no randomization needed on text.
# ---------------------------------------------------------------------------

ALERT_DEFINITIONS: List[dict] = [
    # ── CRITICAL (5) ────────────────────────────────────────────────────────
    {
        "title": "MOB6 Retention Critical Drop — Charlotte DMA",
        "severity": "critical",
        "category": "performance",
        "message": (
            "MOB6 Retention dropped 2.3pts below target in Charlotte DMA "
            "(actual 71.4% vs. 73.7% target). Immediate review of onboarding "
            "sequence and early-lifecycle engagement campaigns recommended."
        ),
    },
    {
        "title": "SEM Non-Branded CPC Threshold Exceeded",
        "severity": "critical",
        "category": "budget",
        "message": (
            "SEM non-branded CPC reached $5.84 against a $5.00 threshold. "
            "Auction pressure from two new competitor entrants detected in "
            "Atlanta and Tampa DMAs. Pause low-ROAS ad groups immediately."
        ),
    },
    {
        "title": "App Completion Rate Declined 3.2pts WoW",
        "severity": "critical",
        "category": "performance",
        "message": (
            "Mobile app account-opening completion rate fell from 61.8% to 58.6% "
            "week-over-week (WoW). Drop concentrated in iOS 17.4 users on the "
            "identity-verification step. Engineering escalation in progress."
        ),
    },
    {
        "title": "Q2 Paid Search Budget 92% Exhausted — 18 Days Remaining",
        "severity": "critical",
        "category": "budget",
        "message": (
            "Paid search Q2 budget is 92% exhausted with 18 days left in the "
            "quarter. Current burn rate will deplete remaining $47,200 in ~6 days. "
            "Recommend immediate reallocation from display or pause low-priority campaigns."
        ),
    },
    {
        "title": "LTV Model Score Drift Detected",
        "severity": "critical",
        "category": "system",
        "message": (
            "The BEI/LTV scoring pipeline produced out-of-range scores (>1.0) for "
            "1,247 records in the nightly batch. Root cause under investigation — "
            "likely a feature normalization issue introduced in yesterday's model "
            "deployment. Scoring paused; previous scores active."
        ),
    },

    # ── WARNING (13) ────────────────────────────────────────────────────────
    {
        "title": "Email Open Rate Below 15% Threshold — Q2 Mortgage Campaign",
        "severity": "warning",
        "category": "performance",
        "message": (
            "Q2 Mortgage Promo email campaign open rate dropped to 12.3%, "
            "below the 15% benchmark. Subject line A/B test results pending; "
            "consider pausing sends until creative refresh is complete."
        ),
    },
    {
        "title": "Display CPM Spiked 22% in Houston DMA",
        "severity": "warning",
        "category": "budget",
        "message": (
            "Display CPM in Houston DMA rose from $8.40 to $10.24 (+22%) over "
            "the last 7 days, consistent with increased local advertiser competition "
            "during tax season. Monitor daily; trigger budget shift if CPM exceeds $11.50."
        ),
    },
    {
        "title": "Competitor Chase Launched Checking Offer in 4 DMAs",
        "severity": "warning",
        "category": "competitor",
        "message": (
            "Chase Bank activated a new 'Secure Checking $300 bonus' offer in "
            "New York, Philadelphia, Washington DC, and Charlotte. Offer targets "
            "25-40 primary banking segment — overlaps directly with our Q2 "
            "acquisition cohort. Recommend counter-offer analysis within 48 hours."
        ),
    },
    {
        "title": "Funnel Drop-Off Rate Elevated at Application Step",
        "severity": "warning",
        "category": "performance",
        "message": (
            "Application step drop-off rate increased to 38.1% (vs. 31.5% baseline). "
            "Heat-map analysis shows friction on the SSN field in mobile web flow. "
            "UX team has been notified; estimated fix ETA 5 business days."
        ),
    },
    {
        "title": "MOB12 Retention Trending Below Target — Tampa-St. Petersburg",
        "severity": "warning",
        "category": "performance",
        "message": (
            "MOB12 Retention in Tampa-St. Petersburg DMA is tracking at 61.2%, "
            "2.1pts below the 63.3% target. Early warning signals suggest elevated "
            "churn among fee-sensitive checking customers. Lifecycle nurture "
            "sequence update in review."
        ),
    },
    {
        "title": "Social Ad Frequency Cap Exceeded — Q2 Savings Push",
        "severity": "warning",
        "category": "performance",
        "message": (
            "Average ad frequency for Q2 Savings Push social campaign reached 6.8x "
            "per user over 7 days (cap: 5x). Audience fatigue risk elevated. "
            "Expand lookalike seed audience or introduce creative rotation."
        ),
    },
    {
        "title": "Direct Mail ROAS Below 3.0x in Two Markets",
        "severity": "warning",
        "category": "budget",
        "message": (
            "Direct mail ROAS for the Spring Checking Offer 2026 campaign fell below "
            "3.0x in Cleveland-Akron (2.61x) and Nashville (2.74x). Consider "
            "reallocating remaining mail drops to higher-performing DMAs (Atlanta 4.2x, "
            "Denver 3.9x)."
        ),
    },
    {
        "title": "Wells Fargo Reactivated Mortgage Rate Match Program",
        "severity": "warning",
        "category": "competitor",
        "message": (
            "Wells Fargo resumed its mortgage rate-match guarantee promotion in "
            "Dallas-Ft. Worth and Houston. Program matches any competitor's 30-year "
            "fixed rate +0.125%. Impact on our mortgage funnel volume will be visible "
            "in next week's cohort data."
        ),
    },
    {
        "title": "Conversion Rate Declined 1.8pts MoM — Paid Search",
        "severity": "warning",
        "category": "performance",
        "message": (
            "Paid search blended conversion rate declined from 5.4% to 3.6% "
            "month-over-month (MoM). Non-branded keywords driving most of the "
            "degradation. Landing page A/B test scheduled to launch Monday."
        ),
    },
    {
        "title": "ETL Pipeline Delay — KPI Summary Table 4 Hours Behind",
        "severity": "warning",
        "category": "system",
        "message": (
            "Nightly KPI summary ETL job ran 4 hours behind schedule (completed "
            "08:14 ET vs. target 04:00 ET). Cause: upstream campaign data API "
            "latency spike. Dashboards may reflect stale metrics. Next run scheduled "
            "for tonight at 04:00 ET."
        ),
    },
    {
        "title": "CPA Rising for Auto Loan Campaigns — Phoenix",
        "severity": "warning",
        "category": "performance",
        "message": (
            "Cost per acquired auto loan customer in Phoenix DMA increased to $312 "
            "vs. $245 target (+27%). Bid strategy adjustment and negative keyword "
            "expansion in progress. Review in 7 days."
        ),
    },
    {
        "title": "Budget Pacing Alert — Email Q2 Overpacing by 14%",
        "severity": "warning",
        "category": "budget",
        "message": (
            "Email channel is currently pacing 14% ahead of the Q2 plan "
            "($284k actual vs. $249k planned at this point in the quarter). "
            "If unchecked, projected Q2 email spend is $378k vs. $330k budget. "
            "Recommend reducing send frequency for non-priority segments."
        ),
    },

    # ── INFO (17) ────────────────────────────────────────────────────────────
    {
        "title": "Q2 Acquisition Campaign Launched — 8 DMAs",
        "severity": "info",
        "category": "performance",
        "message": (
            "Q2 Acquisition campaign successfully activated across 8 DMAs: "
            "New York, Chicago, Atlanta, Houston, Dallas-Ft. Worth, Phoenix, "
            "Denver, and Charlotte. Initial impression delivery tracking on target "
            "at 98.4% of forecast pace."
        ),
    },
    {
        "title": "New Cohort Defined: Spring 2026 Mobile-First Applicants",
        "severity": "info",
        "category": "performance",
        "message": (
            "A new cohort — Spring 2026 Mobile-First Applicants (n=12,847) — has "
            "been created in the cohort builder. Cohort covers mobile web and app "
            "application completions from 2026-03-01 to 2026-04-30. MOB1 benchmarks "
            "will be available by 2026-06-01."
        ),
    },
    {
        "title": "BEI Score Refresh Complete — 98.3% Coverage",
        "severity": "info",
        "category": "system",
        "message": (
            "Weekly BEI (Behavioral Engagement Index) score refresh completed. "
            "Coverage: 98.3% of active customer records scored. 1.7% excluded due "
            "to insufficient activity history (< 60 days). Next refresh scheduled "
            "in 7 days."
        ),
    },
    {
        "title": "Social ROAS Improved 0.4x QoQ — Q1 Final Report",
        "severity": "info",
        "category": "performance",
        "message": (
            "Q1 social channel ROAS finalized at 3.4x vs. Q4 2025's 3.0x, a +0.4x "
            "improvement driven by creative optimization and audience refinement. "
            "This is the third consecutive quarter of ROAS improvement for social."
        ),
    },
    {
        "title": "Simulator Baseline Benchmarks Updated",
        "severity": "info",
        "category": "system",
        "message": (
            "Marketing mix simulator baseline benchmarks refreshed with Q1 2026 "
            "actuals. Updated metrics include: blended CPA ($188), organic share "
            "(22%), and channel ROAS coefficients. Preset scenarios have been "
            "recalibrated accordingly."
        ),
    },
    {
        "title": "Competitor Intel: Bank of America Digital Checking Push",
        "severity": "info",
        "category": "competitor",
        "message": (
            "Bank of America launched a digital-first checking account campaign "
            "targeting 18-30 year olds with zero-fee positioning. Campaign visible "
            "on Meta and YouTube. No immediate threat to our primary acquisition "
            "segments detected; monitoring for DMA overlap."
        ),
    },
    {
        "title": "Q2 Budget Allocation Approved",
        "severity": "info",
        "category": "budget",
        "message": (
            "Q2 2026 channel budget allocation approved by leadership: Paid Search "
            "$420k (38%), Social $275k (25%), Email $110k (10%), Display $165k (15%), "
            "Direct Mail $132k (12%). Total: $1.102M. Activation in progress."
        ),
    },
    {
        "title": "Funnel Volume Increased 8.2% WoW — Mortgage",
        "severity": "info",
        "category": "performance",
        "message": (
            "Mortgage application funnel volume grew 8.2% week-over-week, reaching "
            "3,241 applications this week. Driven by rate-favorable news cycle and "
            "paid search volume lift in Dallas-Ft. Worth and Houston. Conversion "
            "rates stable at 5.1%."
        ),
    },
    {
        "title": "NPS Score Updated — Q1 2026 Customer Survey",
        "severity": "info",
        "category": "performance",
        "message": (
            "Q1 2026 customer NPS score finalized at 42 (vs. Q4 2025: 39, +3pts). "
            "Top drivers of improvement: mobile app experience (+7pts) and onboarding "
            "speed (+5pts). Detractor themes centered on branch availability and "
            "wait times."
        ),
    },
    {
        "title": "LTV Model v3.2 Deployed to Production",
        "severity": "info",
        "category": "system",
        "message": (
            "LTV model v3.2 successfully deployed. Key changes: added MOB18 "
            "retention feature, recalibrated product cross-sell coefficients, "
            "improved AUC from 0.78 to 0.82. Shadow scoring will run in parallel "
            "for 14 days before full cutover."
        ),
    },
    {
        "title": "Seasonal Uplift Alert: Memorial Day Campaign Window Opens",
        "severity": "info",
        "category": "performance",
        "message": (
            "Memorial Day campaign activation window opens 2026-05-18. Historical "
            "data shows +12-18% lift in checking and savings acquisition during "
            "the Memorial Day window (May 18-27). Ensure creative assets and "
            "budgets are staged by 2026-05-15."
        ),
    },
    {
        "title": "Display Viewability Score Improved to 72%",
        "severity": "info",
        "category": "performance",
        "message": (
            "Display ad viewability improved from 64% to 72% following the "
            "programmatic partner optimization completed last week. Industry "
            "benchmark is 70%. CPM impact was neutral; no additional cost "
            "to achieve the improvement."
        ),
    },
    {
        "title": "Cohort MOB6 Report Ready: Q3 2025 Acquisition Cohort",
        "severity": "info",
        "category": "performance",
        "message": (
            "MOB6 analysis for the Q3 2025 Acquisition Cohort (n=18,432) is "
            "complete. Retention rate: 74.1% (vs. 73.0% benchmark, +1.1pts). "
            "Paid search and social sub-cohorts outperformed; direct mail "
            "sub-cohort slightly below benchmark at 71.6%."
        ),
    },
    {
        "title": "FDIC Benchmark Data Refreshed — Q4 2025",
        "severity": "info",
        "category": "system",
        "message": (
            "FDIC deposit market share benchmarks updated with Q4 2025 data. "
            "Our deposit share in 3 of our top 5 DMAs improved slightly. "
            "Full analysis available in the simulator benchmark module."
        ),
    },
    {
        "title": "Keyword Expansion Complete — Personal Loan Campaign",
        "severity": "info",
        "category": "performance",
        "message": (
            "Personal loan SEM keyword expansion completed: 847 new long-tail "
            "keywords added across 14 ad groups. Expected incremental impressions: "
            "+22k/week. Quality score monitoring will begin 72 hours post-launch."
        ),
    },
    {
        "title": "Email Deliverability Rate Stable at 99.1%",
        "severity": "info",
        "category": "system",
        "message": (
            "Monthly email deliverability audit complete. Deliverability rate: 99.1% "
            "(bounce rate 0.7%, spam complaint rate 0.09%). All domain reputation "
            "metrics in good standing. No action required."
        ),
    },
    {
        "title": "Competitor Rate Watch: Citizens Bank Savings Rate Increase",
        "severity": "info",
        "category": "competitor",
        "message": (
            "Citizens Bank increased their high-yield savings APY from 4.25% to "
            "4.50% effective 2026-05-06. This positions them 25bps above our "
            "current savings offer. Pricing team has been notified for review."
        ),
    },
]


# ---------------------------------------------------------------------------
# Build DataFrame
# ---------------------------------------------------------------------------

def build_rows() -> pd.DataFrame:
    """Construct the alerts DataFrame with timestamps and read/resolved flags."""
    rows = []
    total = len(ALERT_DEFINITIONS)

    # Pre-assign resolved and read states deterministically
    # ~40% resolved, ~55% read
    for i, defn in enumerate(ALERT_DEFINITIONS):
        now = TODAY

        # Spread created_at evenly across last 30 days, jittered by index
        days_ago = (total - i) * (30 / total) + (i % 3) * 0.5
        created_at = WINDOW_START + timedelta(days=30 - days_ago)
        updated_at = created_at + timedelta(hours=(i % 12) + 1)

        # Resolved: criticals are either fresh (not resolved) or older (resolved)
        # Roughly 40% of all alerts resolved
        is_resolved = (i % 5 != 0)  # 80% resolved initially — refine below
        # Keep more critical ones unresolved (active)
        if defn["severity"] == "critical":
            is_resolved = (i % 3 == 0)  # ~33% of criticals resolved
        elif defn["severity"] == "warning":
            is_resolved = (i % 2 == 0)  # ~50% of warnings resolved
        else:
            is_resolved = (i % 3 != 0)  # ~67% of infos resolved

        resolved_at = None
        if is_resolved:
            resolve_hours = (i % 24) + 2
            resolved_at = updated_at + timedelta(hours=resolve_hours)
            # resolved_at can't be in the future
            if resolved_at > now:
                resolved_at = now - timedelta(hours=1)

        # is_read: unread = recent + unresolved alerts, read = older/resolved
        is_read = is_resolved or (days_ago > 10)

        rows.append({
            "id":          str(uuid.uuid4()),
            "title":       defn["title"],
            "severity":    defn["severity"],
            "category":    defn["category"],
            "message":     defn["message"],
            "is_read":     bool(is_read),
            "resolved_at": resolved_at,
            "created_at":  created_at,
            "updated_at":  updated_at,
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Pandera schema
# ---------------------------------------------------------------------------

ALERTS_SCHEMA = DataFrameSchema(
    {
        "id":       Column(str, nullable=False),
        "title":    Column(str, nullable=False),
        "severity": Column(str, Check.isin(SEVERITIES)),
        "category": Column(str, Check.isin(CATEGORIES)),
        "message":  Column(str, nullable=False),
        "is_read":  Column(bool, nullable=False),
        # resolved_at is nullable — pandera allows nullable=True
        "resolved_at": Column("object", nullable=True),
        "created_at":  Column("object", nullable=False),
        "updated_at":  Column("object", nullable=False),
    },
    checks=[
        Check(lambda df: len(df) >= 30,
              error="Expected >= 30 alert rows"),
        Check(lambda df: (df["severity"] == "critical").sum() >= 3,
              error="Expected >= 3 critical alerts"),
        Check(lambda df: (df["severity"] == "warning").sum() >= 10,
              error="Expected >= 10 warning alerts"),
        Check(lambda df: (df["severity"] == "info").sum() >= 15,
              error="Expected >= 15 info alerts"),
        Check(lambda df: df["category"].isin(CATEGORIES).all(),
              error="All categories must be valid"),
        Check(lambda df: df["is_read"].dtype == bool or df["is_read"].dtype == object,
              error="is_read must be boolean"),
    ],
    coerce=True,
)


# ---------------------------------------------------------------------------
# Seed function
# ---------------------------------------------------------------------------

def seed(verbose: bool = True) -> pd.DataFrame:
    """
    Build and insert alert seed data into DuckDB.

    Idempotent: DELETE + INSERT on alerts table.
    Returns the alerts DataFrame.
    """
    df = build_rows()

    # Validate before writing
    ALERTS_SCHEMA.validate(df)

    conn = get_connection()
    try:
        conn.execute("DELETE FROM alerts")
        conn.register("alerts_df", df)
        conn.execute("""
            INSERT INTO alerts
                (id, title, severity, category, message,
                 is_read, resolved_at, created_at, updated_at)
            SELECT id, title, severity, category, message,
                   is_read, resolved_at, created_at, updated_at
            FROM alerts_df
        """)
        conn.commit()
    finally:
        conn.unregister("alerts_df")
        conn.close()

    if verbose:
        sev_counts = df["severity"].value_counts().to_dict()
        cat_counts = df["category"].value_counts().to_dict()
        resolved_n = df["resolved_at"].notna().sum()
        unread_n = (~df["is_read"]).sum()
        print(f"[seed_alerts] Inserted {len(df)} rows into alerts")
        print(f"  Severity:  {sev_counts}")
        print(f"  Category:  {cat_counts}")
        print(f"  Resolved:  {resolved_n} / {len(df)}")
        print(f"  Unread:    {unread_n} / {len(df)}")

    return df


if __name__ == "__main__":
    seed()
