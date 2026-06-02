"""
Product & Experience Data Loaders (APE-112 / APE-20d)
------------------------------------------------------
Three sections of data for the Product & Experience page:

  1. Product Pipeline Tracker  — status-tagged product items with category breakdown
  2. Digital Experience Roadmap — Gantt tasks grouped into waves
  3. Testing Velocity Tracker  — A/B test results with sparkline trend data

All data falls back to deterministic seed if the DB table is absent.
"""

from __future__ import annotations

import datetime
import random
from typing import Any

import numpy as np
import pandas as pd

try:
    import duckdb as _duckdb  # noqa: F401 — availability probe only
    _DUCKDB_AVAILABLE = True
except ImportError:
    _DUCKDB_AVAILABLE = False

_RNG = np.random.default_rng(42)

# ── Constants ──────────────────────────────────────────────────────────────────

PRODUCT_STATUSES = ["Discovery", "In Development", "In Review", "Launched", "On Hold"]

STATUS_SEVERITY = {
    "Discovery": "info",
    "In Development": "warning",
    "In Review": "info",
    "Launched": "success",
    "On Hold": "error",
}

PRODUCT_CATEGORIES = [
    "Digital Onboarding",
    "Mobile Banking",
    "Lending",
    "Payments",
    "Deposits",
    "Customer Experience",
]

ROADMAP_WAVES = ["Wave 1 — Foundation", "Wave 2 — Growth", "Wave 3 — Scale"]

ROADMAP_CATEGORIES = [
    "UX/Design",
    "Platform",
    "Analytics",
    "Personalization",
    "Integration",
]

TEST_CATEGORIES = ["Conversion", "Engagement", "Retention", "Funnel", "Onboarding"]

TEST_STATUSES = ["Running", "Complete", "Inconclusive", "Significant Win", "Significant Loss"]

_TODAY = datetime.date.today()

# ── 1. Product Pipeline Tracker ────────────────────────────────────────────────

_PRODUCT_NAMES = [
    "Instant Account Funding",
    "Mobile Check Deposit v3",
    "Credit Card Pre-Approval Flow",
    "HELOC Digital Application",
    "Zelle P2P Upgrade",
    "Savings Goal Planner",
    "Mortgage Rate Lock Widget",
    "Student Loan Refinance Portal",
    "Business Banking Dashboard",
    "Rewards Program Redesign",
    "Account Alerts 2.0",
    "Joint Account Online Open",
    "Auto Loan Origination",
    "Paperless Enrollment Push",
    "Digital Identity Verification",
]


def load_product_pipeline() -> pd.DataFrame:
    """
    Return the product pipeline as a DataFrame.

    Columns
    -------
    Product, Category, Status, Owner, Priority, Est. Launch, Open Issues, Health
    """
    rng = np.random.default_rng(42)
    rows = []
    statuses = PRODUCT_STATUSES
    priorities = ["Critical", "High", "Medium", "Low"]
    owners = ["A. Chen", "M. Rivera", "T. Brooks", "S. Kim", "J. Patel"]

    for i, name in enumerate(_PRODUCT_NAMES):
        status = rng.choice(statuses, p=[0.15, 0.35, 0.20, 0.20, 0.10])
        category = PRODUCT_CATEGORIES[i % len(PRODUCT_CATEGORIES)]
        priority = rng.choice(priorities, p=[0.10, 0.30, 0.40, 0.20])
        owner = owners[i % len(owners)]
        days_out = int(rng.integers(14, 180))
        launch_date = (_TODAY + datetime.timedelta(days=days_out)).strftime("%Y-%m-%d")
        if status == "Launched":
            launch_date = (_TODAY - datetime.timedelta(days=int(rng.integers(7, 90)))).strftime("%Y-%m-%d")
        open_issues = int(rng.integers(0, 12))
        health = "On Track" if open_issues < 5 else ("At Risk" if open_issues < 9 else "Blocked")

        rows.append({
            "Product": name,
            "Category": category,
            "Status": status,
            "Owner": owner,
            "Priority": priority,
            "Est. Launch": launch_date,
            "Open Issues": open_issues,
            "Health": health,
        })

    return pd.DataFrame(rows)


def load_pipeline_category_breakdown() -> pd.DataFrame:
    """
    Return count and percentage of pipeline items per category × status.

    Columns: Category, Status, Count
    """
    df = load_product_pipeline()
    grouped = df.groupby(["Category", "Status"]).size().reset_index(name="Count")
    return grouped


# ── 2. Digital Experience Roadmap ──────────────────────────────────────────────

_ROADMAP_TASKS = [
    # Wave 1
    ("Accessibility Audit", "Wave 1 — Foundation", "UX/Design", -120, -90),
    ("Design System Rebuild", "Wave 1 — Foundation", "UX/Design", -100, -30),
    ("Core Platform Migration", "Wave 1 — Foundation", "Platform", -90, -10),
    ("Analytics Tagging v2", "Wave 1 — Foundation", "Analytics", -80, -20),
    ("SSO Integration", "Wave 1 — Foundation", "Integration", -70, 0),
    # Wave 2
    ("Personalization Engine", "Wave 2 — Growth", "Personalization", 10, 80),
    ("Mobile App Revamp", "Wave 2 — Growth", "UX/Design", 15, 90),
    ("Real-Time Offers", "Wave 2 — Growth", "Personalization", 30, 100),
    ("API Gateway Upgrade", "Wave 2 — Growth", "Platform", 20, 85),
    ("Journey Analytics", "Wave 2 — Growth", "Analytics", 40, 110),
    # Wave 3
    ("AI Chat Assistant", "Wave 3 — Scale", "Platform", 100, 180),
    ("Proactive Nudge Engine", "Wave 3 — Scale", "Personalization", 110, 190),
    ("Next-Best-Action ML", "Wave 3 — Scale", "Analytics", 120, 200),
    ("Unified Profile API", "Wave 3 — Scale", "Integration", 130, 210),
    ("Cross-Channel Attribution", "Wave 3 — Scale", "Analytics", 140, 220),
]

_TASK_STATUSES = {
    "Wave 1 — Foundation": "Complete",
    "Wave 2 — Growth": "In Progress",
    "Wave 3 — Scale": "Planned",
}


def load_roadmap_gantt() -> pd.DataFrame:
    """
    Return Gantt chart data for the Digital Experience Roadmap.

    Columns: Task, Wave, Category, Start, Finish, Status, Duration_Days
    """
    rows = []
    for task, wave, cat, start_offset, end_offset in _ROADMAP_TASKS:
        start = _TODAY + datetime.timedelta(days=start_offset)
        finish = _TODAY + datetime.timedelta(days=end_offset)
        status = _TASK_STATUSES[wave]
        rows.append({
            "Task": task,
            "Wave": wave,
            "Category": cat,
            "Start": start,
            "Finish": finish,
            "Status": status,
            "Duration_Days": (finish - start).days,
        })
    return pd.DataFrame(rows)


def load_roadmap_wave_summary() -> list[dict[str, Any]]:
    """
    Return wave-level summary cards for the roadmap.

    Each dict has: wave, status, tasks_total, tasks_done, pct_complete, target_date
    """
    df = load_roadmap_gantt()
    summaries = []
    for wave in ROADMAP_WAVES:
        wave_df = df[df["Wave"] == wave]
        total = len(wave_df)
        done = len(wave_df[wave_df["Status"] == "Complete"])
        pct = round(done / total * 100) if total else 0
        target = wave_df["Finish"].max()
        summaries.append({
            "wave": wave,
            "status": _TASK_STATUSES[wave],
            "tasks_total": total,
            "tasks_done": done,
            "pct_complete": pct,
            "target_date": target.strftime("%b %Y"),
        })
    return summaries


# ── 3. Testing Velocity Tracker ────────────────────────────────────────────────

_TEST_NAMES = [
    "Homepage Hero CTA Copy",
    "Checking Account Fee Waiver Modal",
    "Mobile App Onboarding Step 3",
    "Savings Rate Highlight Banner",
    "Pre-Approval Offer Placement",
    "Login Page Password UX",
    "Credit Card Rewards Email",
    "HELOC Landing Page Hero",
    "Branch Locator CTA",
    "App Store Rating Prompt",
    "Spending Insights Tooltip",
    "Auto Loan Rate Calculator",
]

_LIFT_BASELINE = 0.0


def load_test_velocity(n_weeks: int = 12) -> pd.DataFrame:
    """
    Return weekly A/B testing velocity metrics.

    Columns: Week, Tests_Running, Tests_Completed, Significant_Wins, Velocity_Score
    """
    rng = np.random.default_rng(7)
    weeks = [(_TODAY - datetime.timedelta(weeks=n_weeks - i)).strftime("%Y-%m-%d")
             for i in range(n_weeks)]
    rows = []
    baseline_velocity = 6.5
    for i, week in enumerate(weeks):
        running = int(rng.integers(4, 10))
        completed = int(rng.integers(1, 5))
        wins = int(rng.integers(0, completed + 1))
        velocity = baseline_velocity + rng.normal(0, 0.8) + i * 0.05
        rows.append({
            "Week": week,
            "Tests_Running": running,
            "Tests_Completed": completed,
            "Significant_Wins": wins,
            "Velocity_Score": round(float(velocity), 2),
        })
    return pd.DataFrame(rows)


def load_ab_test_results() -> pd.DataFrame:
    """
    Return per-test A/B result rows.

    Columns: Test, Category, Status, Control_CVR, Variant_CVR, Lift_Pct,
             Confidence, Start_Date, End_Date, Calls_to_Action
    """
    rng = np.random.default_rng(42)
    rows = []
    for i, name in enumerate(_TEST_NAMES):
        status = rng.choice(
            TEST_STATUSES,
            p=[0.25, 0.30, 0.10, 0.25, 0.10],
        )
        category = TEST_CATEGORIES[i % len(TEST_CATEGORIES)]
        control_cvr = round(float(rng.uniform(0.02, 0.10)), 4)
        lift = round(float(rng.uniform(-0.08, 0.18)), 4)
        variant_cvr = round(control_cvr * (1 + lift), 4)
        confidence = round(float(rng.uniform(0.80, 0.99)), 2)
        start = _TODAY - datetime.timedelta(days=int(rng.integers(30, 90)))
        end = start + datetime.timedelta(days=int(rng.integers(14, 45)))
        rows.append({
            "Test": name,
            "Category": category,
            "Status": status,
            "Control CVR": f"{control_cvr:.2%}",
            "Variant CVR": f"{variant_cvr:.2%}",
            "Lift %": f"{lift * 100:+.1f}%",
            "Lift_raw": lift,
            "Confidence": f"{confidence:.0%}",
            "Confidence_raw": confidence,
            "Start Date": start.strftime("%Y-%m-%d"),
            "End Date": end.strftime("%Y-%m-%d"),
        })
    return pd.DataFrame(rows)


def load_test_sparklines() -> dict[str, list[float]]:
    """
    Return per-metric sparkline series (12 weekly points) for KPI cards.

    Keys: wins_rate, velocity_score, tests_active, lift_avg
    """
    df = load_test_velocity(n_weeks=12)
    rng = np.random.default_rng(99)
    return {
        "wins_rate": list(
            (df["Significant_Wins"] / df["Tests_Completed"].clip(lower=1)).round(2)
        ),
        "velocity_score": list(df["Velocity_Score"]),
        "tests_active": list(df["Tests_Running"].astype(float)),
        "lift_avg": [round(float(rng.uniform(0.01, 0.08)), 3) for _ in range(12)],
    }
