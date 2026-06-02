"""Seed: Product & Experience Module Data (APE-20a)

Generates:
  - 15 ProductInitiative rows  → product_initiatives
  - 12 RoadmapItem rows        → roadmap_items
  - 10 ABTest rows             → ab_tests
  - 12 TestingVelocity rows    → testing_velocity (one per week, last 12 weeks)

Idempotent: DELETE + INSERT on all four tables.

Run:
    python -m src.data.seeds.seed_product_experience
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import date, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema, Check

WORKSPACE = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if WORKSPACE not in sys.path:
    sys.path.insert(0, WORKSPACE)

from src.data.init_db import get_connection  # noqa: E402

SEED = 42
rng = np.random.default_rng(SEED)

# Reference anchor date
TODAY = date(2026, 5, 8)

# ---------------------------------------------------------------------------
# Static initiative IDs (stable across re-seeds for FK integrity)
# ---------------------------------------------------------------------------
_INITIATIVE_IDS = [str(uuid.UUID(int=i)) for i in range(1, 16)]

# ---------------------------------------------------------------------------
# 1. Product Initiatives (15 rows)
# ---------------------------------------------------------------------------

_INITIATIVES_RAW = [
    # (title, description, status, priority, product_area, owner,
    #  target_launch_date, actual_launch_date, hypothesis, success_metric,
    #  baseline_value, target_value, actual_value)
    (
        "Digital Account Opening v3",
        "Redesign the digital account opening flow to reduce drop-off",
        "launched", "p0", "checking", "Sarah Chen",
        date(2026, 2, 1), date(2026, 2, 14),
        "Simplified form reduces abandonment by 20%",
        "application_completion_rate",
        Decimal("0.4200"), Decimal("0.5100"), Decimal("0.5340"),
    ),
    (
        "Savings Goal Builder",
        "In-app goal-based savings feature with automated round-up",
        "launched", "p1", "savings", "Marcus Webb",
        date(2026, 1, 15), date(2026, 1, 22),
        "Goal framing increases savings product adoption",
        "savings_product_attach_rate",
        Decimal("0.1800"), Decimal("0.2400"), Decimal("0.2610"),
    ),
    (
        "Personalized Onboarding Journey",
        "Segment-aware onboarding with dynamic content blocks",
        "in_progress", "p0", "digital_banking", "Priya Nair",
        date(2026, 6, 1), None,
        "Personalized onboarding drives 15% lift in 30-day PFI milestone completion",
        "pfi_30d_completion_rate",
        Decimal("0.5800"), Decimal("0.6700"), None,
    ),
    (
        "Credit Card Rewards Redesign",
        "Revamp rewards dashboard with real-time earn/redeem visibility",
        "in_progress", "p1", "credit_card", "Jordan Ellis",
        date(2026, 5, 15), None,
        "Visible rewards drive monthly active usage",
        "monthly_active_cardholders_pct",
        Decimal("0.5200"), Decimal("0.6000"), None,
    ),
    (
        "Mortgage Pre-Qual Chatbot",
        "AI-assisted pre-qualification flow embedded in mortgage landing page",
        "in_progress", "p1", "mortgage", "Rachel Kim",
        date(2026, 7, 1), None,
        "Chatbot reduces time-to-pre-qual and increases funnel entry",
        "prequalification_start_rate",
        Decimal("0.0820"), Decimal("0.1100"), None,
    ),
    (
        "Push Notification Relevance Engine",
        "ML-ranked push notifications to reduce opt-out rate",
        "in_progress", "p2", "digital_banking", "Alex Tran",
        date(2026, 8, 1), None,
        "Relevant notifications reduce opt-out by 30%",
        "push_opt_out_rate",
        Decimal("0.0950"), Decimal("0.0665"), None,
    ),
    (
        "Zelle Prominence Uplift",
        "Surface Zelle in-app with contextual prompts for eligible P2P moments",
        "discovery", "p1", "digital_banking", "Dana Park",
        date(2026, 9, 1), None,
        "Contextual prompts increase Zelle activation among eligible non-users",
        "zelle_activation_rate_eligible",
        Decimal("0.3100"), Decimal("0.4000"), None,
    ),
    (
        "Home Equity Digital App",
        "End-to-end digital HELOC application replacing paper process",
        "discovery", "p0", "mortgage", "Tom Bradley",
        date(2026, 10, 1), None,
        "Digital flow captures segment currently lost to competitors",
        "heloc_digital_completion_rate",
        Decimal("0.0000"), Decimal("0.3500"), None,
    ),
    (
        "CD Ladder Tool",
        "Interactive CD ladder builder inside savings hub",
        "discovery", "p2", "savings", "Yuki Mori",
        date(2026, 11, 1), None,
        "Visualizing CD laddering increases high-balance CD product attach",
        "cd_product_attach_rate",
        Decimal("0.0450"), Decimal("0.0720"), None,
    ),
    (
        "Business Banking Dashboard Beta",
        "Separate dashboard experience for small business segment",
        "paused", "p1", "business_banking", "Carlos Reyes",
        date(2026, 4, 1), None,
        "Dedicated dashboard improves SMB NPS by 10 points",
        "smb_nps_score",
        Decimal("32.0000"), Decimal("42.0000"), None,
    ),
    (
        "Spend Analytics v2",
        "Enhanced transaction categorization with merchant-level insights",
        "launched", "p2", "digital_banking", "Mia Foster",
        date(2025, 11, 1), date(2025, 11, 8),
        "Spend visibility increases cross-sell propensity",
        "cross_sell_click_rate",
        Decimal("0.0310"), Decimal("0.0430"), Decimal("0.0410"),
    ),
    (
        "Early Payoff Simulator — Auto Loan",
        "In-app tool showing interest savings from extra payments",
        "launched", "p2", "auto_loan", "David Osei",
        date(2025, 12, 15), date(2025, 12, 20),
        "Engagement with payoff tool increases loan retention",
        "auto_loan_12m_retention",
        Decimal("0.8100"), Decimal("0.8500"), Decimal("0.8390"),
    ),
    (
        "App Biometric Streamlining",
        "Remove secondary PIN after biometric auth to reduce friction",
        "launched", "p3", "digital_banking", "Leila Hassan",
        date(2026, 3, 1), date(2026, 3, 5),
        "Removing friction increases daily active sessions",
        "daily_active_users_pct",
        Decimal("0.4800"), Decimal("0.5300"), Decimal("0.5120"),
    ),
    (
        "Cross-sell Modal Sequencing",
        "Dynamic sequencing of in-app cross-sell prompts by LTV segment",
        "cancelled", "p2", "digital_banking", "Noah Wright",
        date(2026, 3, 15), None,
        "Sequenced prompts reduce annoyance while maintaining attach rate",
        "cross_sell_conversion_rate",
        Decimal("0.0220"), Decimal("0.0300"), None,
    ),
    (
        "Greenpath Financial Wellness Integration",
        "Embed financial wellness score and coaching tips in-app",
        "in_progress", "p1", "digital_banking", "Aisha Johnson",
        date(2026, 6, 15), None,
        "Wellness score visibility increases savings product consideration",
        "savings_consideration_rate",
        Decimal("0.2900"), Decimal("0.3800"), None,
    ),
]

# ---------------------------------------------------------------------------
# 2. Roadmap Items (12 rows, spread across 2026 quarters)
# ---------------------------------------------------------------------------

_ROADMAP_RAW = [
    # (initiative_idx, quarter, title, status, team, effort_points, priority, milestone)
    (0,  "2026-Q1", "Form Simplification — Phase 1", "complete",   "Product Engineering", 8,  "must_have",    "MVP"),
    (0,  "2026-Q1", "A/B Test: Short vs Long Form",   "complete",   "Growth",              3,  "must_have",    None),
    (2,  "2026-Q2", "Segment Tagging at Signup",      "in_flight",  "Data Platform",       5,  "must_have",    "Beta"),
    (2,  "2026-Q2", "Dynamic Content Block Engine",   "in_flight",  "Product Engineering", 13, "must_have",    None),
    (3,  "2026-Q2", "Rewards Widget Redesign",        "in_flight",  "Design",              5,  "should_have",  None),
    (4,  "2026-Q3", "Chatbot NLP Integration",        "planned",    "AI/ML",               8,  "must_have",    "Pilot"),
    (5,  "2026-Q3", "Notification Scoring Model v1",  "planned",    "AI/ML",               13, "must_have",    None),
    (6,  "2026-Q3", "Zelle In-app Prompt Library",    "planned",    "Product Engineering", 5,  "should_have",  None),
    (7,  "2026-Q4", "HELOC Digital App — MVP",        "planned",    "Product Engineering", 21, "must_have",    "Alpha"),
    (8,  "2026-Q4", "CD Ladder Visual Builder",       "planned",    "Design",              8,  "nice_to_have", None),
    (14, "2026-Q2", "Wellness Score API Integration", "in_flight",  "Data Platform",       8,  "must_have",    "Beta"),
    (10, "2026-Q2", "Spend Categories v2 Launch",     "complete",   "Product Engineering", 5,  "should_have",  None),
]

# ---------------------------------------------------------------------------
# 3. A/B Tests (10 rows)
# ---------------------------------------------------------------------------

_AB_TESTS_RAW = [
    # (test_name, hypothesis, product_area, status, variant_count,
    #  start_date, end_date, sample_size, traffic_pct, primary_metric,
    #  control_rate, treatment_rate, lift_pct, p_value, is_significant, winner)
    (
        "DAOv3 Short Form vs Long Form",
        "Shorter form reduces drop-off at personal-info step",
        "checking", "complete", 2,
        date(2026, 1, 15), date(2026, 2, 14), 42000,
        Decimal("0.5000"), "application_completion_rate",
        Decimal("0.420000"), Decimal("0.512000"),
        Decimal("0.2190"), Decimal("0.001200"),
        True, "treatment_a",
    ),
    (
        "Savings Goal CTA Variants",
        "Outcome-framed CTA ('Save for a vacation') outperforms generic",
        "savings", "complete", 3,
        date(2026, 1, 22), date(2026, 2, 28), 31000,
        Decimal("0.3300"), "savings_product_attach_rate",
        Decimal("0.180000"), Decimal("0.221000"),
        Decimal("0.2278"), Decimal("0.003100"),
        True, "treatment_b",
    ),
    (
        "Credit Card Hero Image Test",
        "Lifestyle imagery outperforms rewards-table imagery for card apply CTR",
        "credit_card", "complete", 2,
        date(2026, 2, 1), date(2026, 3, 1), 18500,
        Decimal("0.5000"), "apply_ctr",
        Decimal("0.031000"), Decimal("0.033800"),
        Decimal("0.0903"), Decimal("0.041000"),
        False, None,
    ),
    (
        "Push Notification Timing — AM vs PM",
        "Morning delivery increases open rate for balance alerts",
        "digital_banking", "complete", 2,
        date(2026, 2, 14), date(2026, 3, 14), 55000,
        Decimal("0.5000"), "notification_open_rate",
        Decimal("0.120000"), Decimal("0.158000"),
        Decimal("0.3167"), Decimal("0.000300"),
        True, "treatment_a",
    ),
    (
        "Onboarding Progress Bar vs Steps",
        "Visible step count reduces early drop-off",
        "digital_banking", "running", 2,
        date(2026, 4, 1), None, 28000,
        Decimal("0.5000"), "onboarding_completion_rate",
        Decimal("0.620000"), None,
        None, None, None, None,
    ),
    (
        "Mortgage Chatbot Entry Point",
        "Embedded chatbot on mortgage landing page increases pre-qual starts",
        "mortgage", "running", 2,
        date(2026, 4, 15), None, 12000,
        Decimal("0.5000"), "prequalification_start_rate",
        Decimal("0.082000"), None,
        None, None, None, None,
    ),
    (
        "Rewards Dashboard Tabs vs Single View",
        "Tabbed layout reduces confusion and increases redemption CTA clicks",
        "credit_card", "running", 2,
        date(2026, 5, 1), None, 21000,
        Decimal("0.5000"), "rewards_redemption_cta_ctr",
        Decimal("0.094000"), None,
        None, None, None, None,
    ),
    (
        "Spend Analytics Tile Placement",
        "Above-fold placement increases feature discovery and engagement",
        "digital_banking", "complete", 2,
        date(2025, 10, 15), date(2025, 11, 14), 44000,
        Decimal("0.5000"), "spend_analytics_weekly_active_pct",
        Decimal("0.210000"), Decimal("0.247000"),
        Decimal("0.1762"), Decimal("0.000800"),
        True, "treatment_a",
    ),
    (
        "Auto Loan Payoff Simulator Prompt Timing",
        "Showing payoff simulator at 6-month mark increases engagement",
        "auto_loan", "complete", 2,
        date(2025, 11, 1), date(2025, 12, 15), 9800,
        Decimal("0.5000"), "payoff_simulator_engagement_rate",
        Decimal("0.088000"), Decimal("0.121000"),
        Decimal("0.3750"), Decimal("0.002100"),
        True, "treatment_a",
    ),
    (
        "Biometric Auth — Remove Secondary PIN",
        "Removing second factor post-biometric reduces login friction",
        "digital_banking", "complete", 2,
        date(2026, 2, 15), date(2026, 3, 5), 67000,
        Decimal("0.5000"), "daily_active_users_pct",
        Decimal("0.480000"), Decimal("0.511000"),
        Decimal("0.0646"), Decimal("0.012000"),
        True, "treatment_a",
    ),
]

# ---------------------------------------------------------------------------
# 4. Testing Velocity (12 weeks, ending 2026-05-03)
# ---------------------------------------------------------------------------

def _velocity_week_start(offset_weeks: int) -> date:
    # Week 11 = most recent full week ending 2026-05-03
    anchor = date(2026, 2, 9)  # week_start of the oldest week
    return anchor + timedelta(weeks=offset_weeks)


_VELOCITY_RAW = [
    # (week_offset, team, launched, completed, running, winner_rate, avg_duration_days, total_sample)
    (0,  "Product Growth",   1, 0, 3,  Decimal("0.0000"), 21, 12000),
    (1,  "Product Growth",   2, 1, 4,  Decimal("0.5000"), 19, 18400),
    (2,  "Product Growth",   0, 1, 3,  Decimal("1.0000"), 22, 14100),
    (3,  "Product Growth",   1, 2, 2,  Decimal("0.5000"), 20, 24800),
    (4,  "Product Growth",   2, 1, 3,  Decimal("0.0000"), 18, 21300),
    (5,  "Product Growth",   1, 1, 3,  Decimal("1.0000"), 21, 17600),
    (6,  "Product Growth",   2, 2, 3,  Decimal("1.0000"), 22, 31200),
    (7,  "Product Growth",   1, 1, 4,  Decimal("1.0000"), 20, 28500),
    (8,  "Product Growth",   3, 2, 5,  Decimal("0.5000"), 19, 42100),
    (9,  "Product Growth",   1, 2, 4,  Decimal("0.5000"), 21, 35700),
    (10, "Product Growth",   2, 1, 5,  Decimal("1.0000"), 22, 29000),
    (11, "Product Growth",   2, 2, 5,  Decimal("0.5000"), 20, 38900),
]


# ---------------------------------------------------------------------------
# DataFrame builders
# ---------------------------------------------------------------------------

def build_product_initiatives() -> pd.DataFrame:
    now = pd.Timestamp.now()
    rows = []
    for i, rec in enumerate(_INITIATIVES_RAW):
        (title, desc, status, priority, area, owner,
         target_date, actual_date, hypothesis, metric,
         baseline, target, actual) = rec
        rows.append({
            "id":                  _INITIATIVE_IDS[i],
            "title":               title,
            "description":         desc,
            "status":              status,
            "priority":            priority,
            "product_area":        area,
            "owner":               owner,
            "target_launch_date":  target_date,
            "actual_launch_date":  actual_date,
            "hypothesis":          hypothesis,
            "success_metric":      metric,
            "baseline_value":      float(baseline),
            "target_value":        float(target),
            "actual_value":        float(actual) if actual is not None else None,
            "created_at":          now,
            "updated_at":          now,
        })
    return pd.DataFrame(rows)


def build_roadmap_items() -> pd.DataFrame:
    now = pd.Timestamp.now()
    rows = []
    for (init_idx, quarter, title, status, team, effort, priority, milestone) in _ROADMAP_RAW:
        rows.append({
            "id":              str(uuid.uuid4()),
            "initiative_id":   _INITIATIVE_IDS[init_idx],
            "quarter":         quarter,
            "title":           title,
            "status":          status,
            "team":            team,
            "effort_points":   effort,
            "priority":        priority,
            "milestone":       milestone,
            "created_at":      now,
            "updated_at":      now,
        })
    return pd.DataFrame(rows)


def build_ab_tests() -> pd.DataFrame:
    now = pd.Timestamp.now()
    rows = []
    for rec in _AB_TESTS_RAW:
        (test_name, hypothesis, product_area, status, variant_count,
         start_date, end_date, sample_size, traffic_pct, primary_metric,
         control_rate, treatment_rate, lift_pct, p_value,
         is_significant, winner) = rec
        rows.append({
            "id":                    str(uuid.uuid4()),
            "test_name":             test_name,
            "hypothesis":            hypothesis,
            "product_area":          product_area,
            "status":                status,
            "variant_count":         variant_count,
            "start_date":            start_date,
            "end_date":              end_date,
            "sample_size":           sample_size,
            "traffic_allocation_pct": float(traffic_pct),
            "primary_metric":        primary_metric,
            "control_rate":          float(control_rate),
            "treatment_rate":        float(treatment_rate) if treatment_rate is not None else None,
            "lift_pct":              float(lift_pct) if lift_pct is not None else None,
            "p_value":               float(p_value) if p_value is not None else None,
            "is_significant":        is_significant,
            "winner":                winner,
            "created_at":            now,
            "updated_at":            now,
        })
    return pd.DataFrame(rows)


def build_testing_velocity() -> pd.DataFrame:
    now = pd.Timestamp.now()
    rows = []
    for (offset, team, launched, completed, running,
         winner_rate, avg_dur, sample) in _VELOCITY_RAW:
        rows.append({
            "id":                     str(uuid.uuid4()),
            "week_start":             _velocity_week_start(offset),
            "team":                   team,
            "tests_launched":         launched,
            "tests_completed":        completed,
            "tests_running":          running,
            "winner_rate":            float(winner_rate),
            "avg_test_duration_days": avg_dur,
            "total_sample_size":      sample,
            "created_at":             now,
            "updated_at":             now,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Pandera schemas
# ---------------------------------------------------------------------------

_INITIATIVE_STATUSES = ["discovery", "in_progress", "launched", "paused", "cancelled"]
_INITIATIVE_PRIORITIES = ["p0", "p1", "p2", "p3"]

INITIATIVE_SCHEMA = DataFrameSchema(
    {
        "id":                 Column(str, nullable=False),
        "title":              Column(str, nullable=False),
        "status":             Column(str, Check.isin(_INITIATIVE_STATUSES)),
        "priority":           Column(str, Check.isin(_INITIATIVE_PRIORITIES)),
        "product_area":       Column(str, nullable=False),
        "owner":              Column(str, nullable=False),
        "baseline_value":     Column(float, Check.ge(0)),
        "target_value":       Column(float, Check.ge(0)),
    },
    checks=[
        Check(lambda df: len(df) == 15, error="Expected 15 product initiatives"),
    ],
    coerce=True,
)

_ROADMAP_STATUSES = ["planned", "in_flight", "complete", "deferred"]
_ROADMAP_PRIORITIES = ["must_have", "should_have", "nice_to_have"]

ROADMAP_SCHEMA = DataFrameSchema(
    {
        "id":            Column(str, nullable=False),
        "initiative_id": Column(str, nullable=False),
        "quarter":       Column(str, Check.str_matches(r"^\d{4}-Q[1-4]$")),
        "status":        Column(str, Check.isin(_ROADMAP_STATUSES)),
        "priority":      Column(str, Check.isin(_ROADMAP_PRIORITIES)),
        "effort_points": Column(int, [Check.ge(1), Check.le(21)]),
    },
    checks=[
        Check(lambda df: len(df) == 12, error="Expected 12 roadmap items"),
    ],
    coerce=True,
)

_TEST_STATUSES = ["draft", "running", "complete", "stopped"]

ABTEST_SCHEMA = DataFrameSchema(
    {
        "id":                     Column(str, nullable=False),
        "test_name":              Column(str, nullable=False),
        "status":                 Column(str, Check.isin(_TEST_STATUSES)),
        "variant_count":          Column(int, [Check.ge(2), Check.le(5)]),
        "sample_size":            Column(int, Check.ge(0)),
        "traffic_allocation_pct": Column(float, [Check.ge(0), Check.le(1)]),
        "control_rate":           Column(float, [Check.ge(0), Check.le(1)]),
    },
    checks=[
        Check(lambda df: len(df) == 10, error="Expected 10 A/B tests"),
    ],
    coerce=True,
)

VELOCITY_SCHEMA = DataFrameSchema(
    {
        "id":                     Column(str, nullable=False),
        "team":                   Column(str, nullable=False),
        "tests_launched":         Column(int, Check.ge(0)),
        "tests_completed":        Column(int, Check.ge(0)),
        "tests_running":          Column(int, Check.ge(0)),
        "winner_rate":            Column(float, [Check.ge(0), Check.le(1)]),
        "avg_test_duration_days": Column(int, Check.ge(0)),
        "total_sample_size":      Column(int, Check.ge(0)),
    },
    checks=[
        Check(lambda df: len(df) == 12, error="Expected 12 velocity rows"),
    ],
    coerce=True,
)


# ---------------------------------------------------------------------------
# DB persistence helpers
# ---------------------------------------------------------------------------

def _upsert(conn, table: str, df: pd.DataFrame, reg_name: str, cols: list[str]) -> None:
    conn.execute(f"DELETE FROM {table}")
    conn.register(reg_name, df)
    col_list = ", ".join(f'"{c}"' for c in cols)
    conn.execute(f"INSERT INTO {table} ({col_list}) SELECT {col_list} FROM {reg_name}")
    try:
        conn.unregister(reg_name)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public seed entry point
# ---------------------------------------------------------------------------

def seed(verbose: bool = True) -> dict[str, pd.DataFrame]:
    initiatives_df = build_product_initiatives()
    roadmap_df = build_roadmap_items()
    abtests_df = build_ab_tests()
    velocity_df = build_testing_velocity()

    # Validate
    INITIATIVE_SCHEMA.validate(initiatives_df)
    ROADMAP_SCHEMA.validate(roadmap_df)
    ABTEST_SCHEMA.validate(abtests_df)
    VELOCITY_SCHEMA.validate(velocity_df)

    conn = get_connection()
    try:
        _upsert(conn, "product_initiatives", initiatives_df, "_init_df", [
            "id", "title", "description", "status", "priority", "product_area",
            "owner", "target_launch_date", "actual_launch_date", "hypothesis",
            "success_metric", "baseline_value", "target_value", "actual_value",
            "created_at", "updated_at",
        ])
        _upsert(conn, "roadmap_items", roadmap_df, "_road_df", [
            "id", "initiative_id", "quarter", "title", "status", "team",
            "effort_points", "priority", "milestone", "created_at", "updated_at",
        ])
        _upsert(conn, "ab_tests", abtests_df, "_ab_df", [
            "id", "test_name", "hypothesis", "product_area", "status",
            "variant_count", "start_date", "end_date", "sample_size",
            "traffic_allocation_pct", "primary_metric", "control_rate",
            "treatment_rate", "lift_pct", "p_value", "is_significant", "winner",
            "created_at", "updated_at",
        ])
        _upsert(conn, "testing_velocity", velocity_df, "_vel_df", [
            "id", "week_start", "team", "tests_launched", "tests_completed",
            "tests_running", "winner_rate", "avg_test_duration_days",
            "total_sample_size", "created_at", "updated_at",
        ])
        conn.commit()
    finally:
        conn.close()

    if verbose:
        print(f"[seed_product_experience] product_initiatives: {len(initiatives_df)} rows")
        print(f"[seed_product_experience] roadmap_items:        {len(roadmap_df)} rows")
        print(f"[seed_product_experience] ab_tests:             {len(abtests_df)} rows")
        print(f"[seed_product_experience] testing_velocity:     {len(velocity_df)} rows")

    return {
        "product_initiatives": initiatives_df,
        "roadmap_items":       roadmap_df,
        "ab_tests":            abtests_df,
        "testing_velocity":    velocity_df,
    }


if __name__ == "__main__":
    seed()
