"""Seed: Ops Command Center Data  (APE-21b / APE-116)

Generates seed data for all 5 ops tables, meeting acceptance criteria:
  - calendar_events:          35 events, 3 months (Mar–May 2026), all 6 event types
  - approval_items:           15 items including ≥10 pending, with realistic dollar impacts
  - system_health_checks:     18 checks across all 6 SystemCategory values
  - competitive_intel_items:  20 items across 5 competitors & 6 categories
  - team_capacity:            96 rows (8 teams × 12 monthly periods: 2025-06 → 2026-05)

Idempotent: DELETE + INSERT on all five tables.

Run:
    python -m src.data.seeds.seed_ops
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema, Check

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
WORKSPACE = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if WORKSPACE not in sys.path:
    sys.path.insert(0, WORKSPACE)

from src.data.init_db import get_connection  # noqa: E402
from src.data.seeds._dates import (
    YESTERDAY,
    NOW as _NOW,
    TWELVE_MONTH_STRINGS,
)

SEED = 2026
rng = np.random.default_rng(SEED)

TODAY = YESTERDAY
NOW = _NOW

# Shift all hardcoded dates relative to the original anchor (2026-05-08)
_ORIG_ANCHOR = date(2026, 5, 8)
_SHIFT = timedelta(days=(TODAY - _ORIG_ANCHOR).days)


def _dt(year, month, day, hour=0, minute=0, second=0):
    """Create a datetime shifted relative to the original anchor."""
    return datetime(year, month, day, hour, minute, second) + _SHIFT


def _d(year, month, day):
    """Create a date shifted relative to the original anchor."""
    return date(year, month, day) + _SHIFT


# ---------------------------------------------------------------------------
# 1. Calendar Events  (35 events: Mar–May 2026, all 6 event types)
# ---------------------------------------------------------------------------
# Columns: title, event_type, status, start_dt, end_dt,
#          owner, attendees, description, related_campaign_id

_CALENDAR_EVENTS_RAW: list[tuple] = [
    # ── March 2026 ──────────────────────────────────────────────────────────
    (
        "Q2 Checking Acquisition Campaign Launch",
        "campaign_launch", "completed",
        _dt(2026, 3, 3, 9, 0), _dt(2026, 3, 3, 10, 0),
        "CMO", "Brand, Performance Media, Creative",
        "Multi-channel Q2 checking acquisition push across SEM, social, CTV. Target: 12,000 net new accounts.",
        None,
    ),
    (
        "Spring Home Equity Campaign Kickoff",
        "campaign_launch", "completed",
        _dt(2026, 3, 10, 10, 0), _dt(2026, 3, 10, 11, 0),
        "VP Performance Media", "SEM Lead, Social Lead, Creative Director",
        "HELOC/HELOAN spring season launch. Rate-feature focus in Tier 1 markets.",
        None,
    ),
    (
        "Q1 Campaign Performance Full Review",
        "review_cycle", "completed",
        _dt(2026, 3, 5, 13, 0), _dt(2026, 3, 5, 15, 0),
        "CMO", "CMO, Analytics, Agency Partners",
        "Q1 full-funnel retrospective: spend vs. plan, conversions, CPA by channel, brand lift results.",
        None,
    ),
    (
        "Checking Creative Compliance Review",
        "review_cycle", "completed",
        _dt(2026, 3, 12, 10, 0), _dt(2026, 3, 12, 11, 0),
        "Creative Director", "Creative, Legal, Compliance",
        "Review updated checking creative pack. UDAP rate-claim language sign-off required before Q2.",
        None,
    ),
    (
        "UDAP Creative Compliance Deadline — Q2 Assets",
        "compliance_deadline", "completed",
        _dt(2026, 3, 14, 17, 0), _dt(2026, 3, 14, 17, 30),
        "Compliance Director", "Legal, Compliance, Creative, Performance Media",
        "All Q2 paid creative must receive Compliance approval before trafficking to media platforms.",
        None,
    ),
    (
        "Board Marketing Update — Q1 Results",
        "exec_briefing", "completed",
        _dt(2026, 3, 20, 15, 0), _dt(2026, 3, 20, 16, 0),
        "CMO", "CMO, CFO, Board Members",
        "Quarterly marketing ROI brief: Q1 spend, pipeline generated, brand lift, LTV impact by cohort.",
        None,
    ),
    (
        "Q1 Budget Reconciliation & Q2 Reforecast",
        "budget_review", "completed",
        _dt(2026, 3, 25, 10, 0), _dt(2026, 3, 25, 12, 0),
        "VP Marketing Finance", "Finance, CMO, Channel Leads",
        "Reconcile Q1 actual vs plan. Ratify Q2 channel budget allocations ($15M total).",
        None,
    ),
    (
        "Marketing All-Hands — March",
        "team_sync", "completed",
        _dt(2026, 3, 6, 12, 0), _dt(2026, 3, 6, 13, 0),
        "CMO", "All Marketing",
        "Monthly all-hands: Q1 recap, Q2 priorities, org announcements.",
        None,
    ),
    (
        "Performance Pod Weekly Sync — March W2",
        "team_sync", "completed",
        _dt(2026, 3, 13, 9, 0), _dt(2026, 3, 13, 9, 30),
        "VP Performance Media", "SEM, Social, Analytics",
        "Weekly pacing review: CPA by channel, A/B test status, bid strategy updates.",
        None,
    ),
    (
        "Fair Lending Geo-Targeting Attestation",
        "compliance_deadline", "completed",
        _dt(2026, 3, 28, 17, 0), _dt(2026, 3, 28, 17, 30),
        "Chief Compliance Officer", "Legal, Performance Media",
        "Confirm geo-targeting parameters comply with CRA and fair lending requirements before Q2 launch.",
        None,
    ),
    (
        "SEO & AEO Quarterly Review",
        "review_cycle", "completed",
        _dt(2026, 3, 19, 9, 0), _dt(2026, 3, 19, 10, 0),
        "SEO Lead", "SEO, Analytics, Product Marketing",
        "Organic performance vs. keyword targets. LLM visibility benchmarks across ChatGPT, Perplexity, Gemini.",
        None,
    ),
    (
        "Auto Loan Rate Promotion — Tier 1 Markets Launch",
        "campaign_launch", "completed",
        _dt(2026, 3, 17, 14, 0), _dt(2026, 3, 17, 15, 0),
        "Product Marketing Lead", "Paid Social, SEM, Email",
        "Targeted rate promo for high-HHI DMAs. 90-day window tied to spring auto season.",
        None,
    ),
    # ── April 2026 ──────────────────────────────────────────────────────────
    (
        "Earth Day Green Banking Campaign Launch",
        "campaign_launch", "completed",
        _dt(2026, 4, 7, 9, 0), _dt(2026, 4, 7, 10, 0),
        "VP Brand", "Brand, Social, PR",
        "ESG brand push tied to Earth Day (Apr 22). Awareness and consideration objectives.",
        None,
    ),
    (
        "Life Events Q2 Campaign Go-Live",
        "campaign_launch", "completed",
        _dt(2026, 4, 7, 8, 0), _dt(2026, 4, 7, 9, 0),
        "VP Performance Media", "Performance Media, Life Events Team",
        "Mover and new-parent segment campaign activation. 8 DMA expansion from Q1.",
        None,
    ),
    (
        "Mid-Q2 Campaign Performance Check-In",
        "review_cycle", "completed",
        _dt(2026, 4, 9, 14, 0), _dt(2026, 4, 9, 15, 0),
        "CMO", "CMO, Analytics, Channel Leads",
        "Q2 pacing review at 6-week mark. Channel reallocation decisions if flagged.",
        None,
    ),
    (
        "Annual Privacy Policy Review Deadline",
        "compliance_deadline", "completed",
        _dt(2026, 4, 11, 17, 0), _dt(2026, 4, 11, 17, 30),
        "Chief Privacy Officer", "Legal, IT, Compliance",
        "Annual review of consumer-facing privacy disclosures and cookie consent banners.",
        None,
    ),
    (
        "Brand Lift Study Readout — Q1 CTV/OLV",
        "review_cycle", "completed",
        _dt(2026, 4, 16, 10, 0), _dt(2026, 4, 16, 11, 0),
        "VP Brand", "Brand, Insights, Media Agency",
        "Kantar brand lift results for Q1 CTV/OLV campaigns across top 10 DMAs.",
        None,
    ),
    (
        "CFO Marketing ROI Briefing — Q2 Forecast",
        "exec_briefing", "scheduled",
        _dt(2026, 4, 22, 15, 0), _dt(2026, 4, 22, 16, 0),
        "CMO", "CMO, CFO, VP Finance",
        "Forward-looking: Q2 projected spend, pipeline, incremental revenue model.",
        None,
    ),
    (
        "Digital Budget Reallocation Review",
        "budget_review", "completed",
        _dt(2026, 4, 8, 11, 0), _dt(2026, 4, 8, 12, 0),
        "VP Marketing Finance", "Finance, SEM Lead, Social Lead",
        "Shift $200K from display to paid social based on Q1 CPA performance data.",
        None,
    ),
    (
        "Marketing All-Hands — April",
        "team_sync", "completed",
        _dt(2026, 4, 3, 12, 0), _dt(2026, 4, 3, 13, 0),
        "CMO", "All Marketing",
        "Monthly all-hands: Q2 priorities, headcount updates, agency partner review.",
        None,
    ),
    (
        "Creative Studio Sprint Review — April",
        "team_sync", "completed",
        _dt(2026, 4, 17, 14, 0), _dt(2026, 4, 17, 15, 0),
        "Creative Director", "Creative, Brand, Product Marketing",
        "Bi-weekly sprint review: asset completion, backlog grooming, Q3 kick-off prep.",
        None,
    ),
    (
        "CAN-SPAM & TCPA Audit Deadline",
        "compliance_deadline", "scheduled",
        _dt(2026, 4, 25, 17, 0), _dt(2026, 4, 25, 17, 30),
        "Compliance Director", "Legal, CRM, Digital Marketing",
        "Confirm all email and SMS sequences comply with CAN-SPAM opt-out and TCPA consent requirements.",
        None,
    ),
    (
        "Agency QBR — Media Agency Performance Review",
        "review_cycle", "scheduled",
        _dt(2026, 4, 30, 13, 0), _dt(2026, 4, 30, 16, 0),
        "CMO", "CMO, Procurement, Media Agency",
        "Q1 agency performance review: SLA audit, optimization recommendations, Q2 roadmap alignment.",
        None,
    ),
    (
        "Savings Rate Promotion Launch — Digital-First",
        "campaign_launch", "completed",
        _dt(2026, 4, 14, 10, 0), _dt(2026, 4, 14, 11, 0),
        "Product Marketing Lead", "Email, SEM, Paid Social",
        "HYSA competitive rate promotion targeting digital-first millennials and Gen Z switchers.",
        None,
    ),
    # ── May 2026 ────────────────────────────────────────────────────────────
    (
        "Graduation Banking Package Campaign Launch",
        "campaign_launch", "in_progress",
        _dt(2026, 5, 1, 9, 0), _dt(2026, 5, 1, 10, 0),
        "VP Brand", "Social, Email, Branch Network",
        "Young adult acquisition tied to graduation season. First checking + savings bundle offer.",
        None,
    ),
    (
        "Marketing All-Hands — May",
        "team_sync", "scheduled",
        _dt(2026, 5, 1, 12, 0), _dt(2026, 5, 1, 13, 0),
        "CMO", "All Marketing",
        "Monthly all-hands: Q2 pacing update, headcount news, competitive landscape.",
        None,
    ),
    (
        "Q2 Pacing Review — Month 1",
        "review_cycle", "in_progress",
        _dt(2026, 5, 6, 14, 0), _dt(2026, 5, 6, 15, 0),
        "CMO", "CMO, Analytics, Channel Leads",
        "First-month Q2 pacing vs. plan. Early warning signals on underperforming channels.",
        None,
    ),
    (
        "Performance Pod Weekly Sync — May W1",
        "team_sync", "in_progress",
        _dt(2026, 5, 8, 9, 0), _dt(2026, 5, 8, 9, 30),
        "VP Performance Media", "SEM, Social, Analytics",
        "Weekly pacing: CPA by channel, competitive SEM activity, A/B test updates.",
        None,
    ),
    (
        "Summer Home Loan Refi Campaign Launch",
        "campaign_launch", "scheduled",
        _dt(2026, 5, 12, 9, 0), _dt(2026, 5, 12, 10, 0),
        "VP Performance Media", "SEM, Social, Email",
        "Rate-sensitive refinance campaign timed to summer purchasing season.",
        None,
    ),
    (
        "CMO Monthly Executive Briefing — May",
        "exec_briefing", "scheduled",
        _dt(2026, 5, 13, 15, 0), _dt(2026, 5, 13, 16, 0),
        "CMO", "CEO, CMO, CHRO",
        "Monthly marketing status to executive team: brand health, growth, retention metrics.",
        None,
    ),
    (
        "Reg E Marketing Disclosure Review",
        "compliance_deadline", "scheduled",
        _dt(2026, 5, 15, 17, 0), _dt(2026, 5, 15, 17, 30),
        "Compliance Director", "Legal, Digital Marketing, Product",
        "Review all digital marketing materials referencing overdraft protection language.",
        None,
    ),
    (
        "Q3 Budget Planning Kickoff",
        "budget_review", "scheduled",
        _dt(2026, 5, 19, 10, 0), _dt(2026, 5, 19, 12, 0),
        "VP Marketing Finance", "Finance, CMO, Channel Leads",
        "Initial Q3 channel budget allocation discussions. Lock final budget by May 30.",
        None,
    ),
    (
        "SEO Technical Audit Results Review",
        "review_cycle", "scheduled",
        _dt(2026, 5, 20, 10, 0), _dt(2026, 5, 20, 11, 0),
        "SEO Lead", "SEO, Engineering, Analytics",
        "Core Web Vitals audit and crawl budget analysis. Prioritize fixes for Q3.",
        None,
    ),
    (
        "Investor Day Marketing Narrative Prep",
        "exec_briefing", "scheduled",
        _dt(2026, 5, 22, 14, 0), _dt(2026, 5, 22, 16, 0),
        "CMO", "CMO, CFO, Investor Relations",
        "Align marketing story for Investor Day (June 10). Revenue growth, digital mix, LTV.",
        None,
    ),
    (
        "Annual Creative Strategy Review",
        "review_cycle", "scheduled",
        _dt(2026, 5, 29, 9, 0), _dt(2026, 5, 29, 11, 0),
        "CMO", "CMO, Creative Director, Brand Team",
        "Full creative strategy evaluation: messaging hierarchy, visual identity refresh considerations.",
        None,
    ),
]


def _build_calendar_events() -> pd.DataFrame:
    rows = []
    for (
        title, event_type, status, start_dt, end_dt,
        owner, attendees, description, related_campaign_id
    ) in _CALENDAR_EVENTS_RAW:
        rows.append({
            "id":                   str(uuid.uuid4()),
            "title":                title,
            "event_type":           event_type,
            "status":               status,
            "start_dt":             start_dt,
            "end_dt":               end_dt,
            "owner":                owner,
            "attendees":            attendees,
            "description":          description,
            "related_campaign_id":  related_campaign_id,
            "created_at":           NOW - timedelta(days=int(rng.integers(1, 14))),
            "updated_at":           NOW,
        })
    return pd.DataFrame(rows)


CALENDAR_SCHEMA = DataFrameSchema(
    {
        "id":         Column(str, Check(lambda s: s.str.len() > 0)),
        "title":      Column(str, Check(lambda s: s.str.len() > 0)),
        "event_type": Column(str, Check.isin([
            "campaign_launch", "review_cycle", "compliance_deadline",
            "exec_briefing", "budget_review", "team_sync", "other",
        ])),
        "status":     Column(str, Check.isin([
            "scheduled", "in_progress", "completed", "cancelled",
        ])),
        "start_dt":   Column("datetime64[ns]"),
        "end_dt":     Column("datetime64[ns]"),
        "owner":      Column(str, Check(lambda s: s.str.len() > 0)),
    },
    coerce=True,
)


# ---------------------------------------------------------------------------
# 2. Approval Items  (15 rows — ≥10 pending, all with realistic dollar impacts)
# ---------------------------------------------------------------------------

_APPROVAL_ITEMS_RAW: list[tuple] = [
    # (title, category, status, priority, requestor, approver,
    #  due_date, resolved_at, budget_impact, notes, artifact_url)

    # ── 10 Pending items ────────────────────────────────────────────────────
    (
        "Q2 SEM Budget Increase — Checking Acquisition +$500K",
        "budget_change", "pending", "urgent",
        "VP Performance Media", "CMO",
        _dt(2026, 5, 10, 17, 0), None,
        Decimal("500000.00"),
        "Competitor SEM spend rising 30% in checking keywords. Defensive uplift to hold impression share.",
        None,
    ),
    (
        "MediaLink Agency Contract Renewal — $1.2M Annual",
        "vendor_contract", "pending", "high",
        "VP Marketing Finance", "CFO",
        _dt(2026, 5, 16, 17, 0), None,
        Decimal("1200000.00"),
        "Annual media planning & buying contract renewal. 3% rate increase negotiated vs. prior year.",
        "https://contracts.example.com/medialink-renewal-2026",
    ),
    (
        "Small Business Banking Campaign Brief — Q2",
        "campaign_brief", "pending", "medium",
        "Product Marketing Lead", "CMO",
        _dt(2026, 5, 13, 17, 0), None,
        Decimal("250000.00"),
        "Full campaign brief for SMB awareness push in Midwest markets. Awaiting CMO sign-off before kick-off.",
        "https://drive.example.com/q2-smb-campaign-brief",
    ),
    (
        "Summer Refi Landing Page — UDAP Compliance Review",
        "compliance", "pending", "high",
        "Digital Marketing Manager", "Compliance Director",
        _dt(2026, 5, 14, 17, 0), None,
        Decimal("0.00"),
        "Rate claims on refi landing page must be reviewed before go-live on May 12.",
        "https://staging.example.com/home-loan/refi-summer",
    ),
    (
        "Nielsen Brand Lift Study Renewal — Annual",
        "vendor_contract", "pending", "medium",
        "VP Brand", "VP Marketing Finance",
        _dt(2026, 5, 20, 17, 0), None,
        Decimal("185000.00"),
        "Annual renewal for Nielsen Brand Impact subscription: awareness, consideration, preference tracking.",
        None,
    ),
    (
        "CTV Creative Refresh — Q3 Video Assets (30s + 15s)",
        "creative", "pending", "medium",
        "Creative Director", "CMO",
        _dt(2026, 5, 23, 17, 0), None,
        Decimal("120000.00"),
        "Production estimate for Q3 CTV spots: 2 × 30s and 4 × 15s across checking, savings, home equity.",
        "https://drive.example.com/q3-ctv-creative-brief",
    ),
    (
        "Salesforce Marketing Cloud License Upgrade",
        "budget_change", "pending", "medium",
        "Marketing Ops Director", "CFO",
        _dt(2026, 5, 28, 17, 0), None,
        Decimal("340000.00"),
        "Upgrade to enterprise tier for AI segmentation and predictive send-time features. Annual incremental cost.",
        None,
    ),
    (
        "Digital Privacy Consent Banner — Legal Sign-Off",
        "compliance", "pending", "urgent",
        "Chief Privacy Officer", "General Counsel",
        _dt(2026, 5, 9, 17, 0), None,
        Decimal("0.00"),
        "Updated consent banner required before May 15 CCPA audit window. Covers web + mobile app.",
        "https://legal.example.com/privacy-consent-2026",
    ),
    (
        "FinFluencer Influencer Program — 6-Month Agreement",
        "vendor_contract", "pending", "low",
        "Social Media Manager", "VP Brand",
        _dt(2026, 5, 30, 17, 0), None,
        Decimal("75000.00"),
        "6-month influencer program across 12 personal finance creators. FTC disclosure language to be confirmed.",
        "https://contracts.example.com/finfluencer-2026",
    ),
    (
        "Home Equity Campaign Creative — Digital Pack v3",
        "creative", "pending", "high",
        "Creative Director", "Compliance Director",
        _dt(2026, 5, 9, 17, 0), None,
        Decimal("0.00"),
        "Final compliance review of 8 display + 4 social assets. Rate claims updated per current offer sheet.",
        "https://drive.example.com/he-creative-v3",
    ),
    # ── 5 Non-pending items (resolved / in-review) ──────────────────────────
    (
        "Brand Media Budget Reallocation — CTV +$200K",
        "budget_change", "approved", "urgent",
        "VP Performance Media", "CFO",
        _dt(2026, 4, 15, 17, 0), _dt(2026, 4, 14, 16, 0),
        Decimal("200000.00"),
        "Approved. CTV performance exceeds benchmark; incremental spend authorized for Q2.",
        None,
    ),
    (
        "Q2 SEM Creative — Mortgage Rate Ad Copy",
        "creative", "approved", "high",
        "SEM Manager", "CMO",
        _dt(2026, 4, 29, 17, 0), _dt(2026, 4, 28, 14, 30),
        Decimal("0.00"),
        "Approved. Rate claims verified against current offer. APR disclaimer updated.",
        "https://drive.example.com/sem-mortgage-apr26",
    ),
    (
        "May Social Paid Creative Batch — Meta",
        "creative", "in_review", "medium",
        "Social Media Manager", "Compliance Director",
        _dt(2026, 5, 10, 17, 0), None,
        Decimal("0.00"),
        "Creative submitted. Compliance reviewing rate claim language on savings ads.",
        "https://drive.example.com/social-may-meta-batch",
    ),
    (
        "Third-Party Data Vendor Renewal — Acxiom",
        "vendor_contract", "rejected", "high",
        "Marketing Ops Director", "CFO",
        _dt(2026, 4, 20, 17, 0), _dt(2026, 4, 19, 10, 0),
        Decimal("480000.00"),
        "Rejected. Current pricing 22% above market. Competitive RFP process initiated.",
        None,
    ),
    (
        "Annual HMDA Data Certification",
        "compliance", "approved", "urgent",
        "Compliance Team", "Chief Compliance Officer",
        _dt(2026, 4, 30, 17, 0), _dt(2026, 4, 29, 11, 0),
        Decimal("0.00"),
        "Certified and filed with CFPB on schedule.",
        None,
    ),
]


def _build_approval_items() -> pd.DataFrame:
    rows = []
    for (
        title, category, status, priority, requestor, approver,
        due_date, resolved_at, budget_impact, notes, artifact_url
    ) in _APPROVAL_ITEMS_RAW:
        rows.append({
            "id":            str(uuid.uuid4()),
            "title":         title,
            "category":      category,
            "status":        status,
            "priority":      priority,
            "requestor":     requestor,
            "approver":      approver,
            "due_date":      due_date,
            "resolved_at":   resolved_at,
            "budget_impact": budget_impact,
            "notes":         notes,
            "artifact_url":  artifact_url,
            "created_at":    NOW - timedelta(days=int(rng.integers(1, 30))),
            "updated_at":    NOW,
        })
    return pd.DataFrame(rows)


APPROVAL_SCHEMA = DataFrameSchema(
    {
        "id":          Column(str),
        "title":       Column(str, Check(lambda s: s.str.len() > 0)),
        "category":    Column(str, Check.isin([
            "creative", "budget_change", "compliance",
            "vendor_contract", "campaign_brief", "other",
        ])),
        "status":      Column(str, Check.isin([
            "pending", "in_review", "approved", "rejected", "escalated",
        ])),
        "priority":    Column(str, Check.isin(["low", "medium", "high", "urgent"])),
        "requestor":   Column(str, Check(lambda s: s.str.len() > 0)),
    },
    coerce=True,
)


# ---------------------------------------------------------------------------
# 3. System Health Checks  (18 rows: 6 systems × 3 snapshots each)
#    All 6 SystemCategory values covered: data_pipeline, api_integration,
#    platform_connection, database, reporting, other
# ---------------------------------------------------------------------------

# Six monitored systems, one per SystemCategory
_SYSTEMS = [
    # (system_name, category, owner_team)
    ("DMP Data Pipeline",         "data_pipeline",       "Marketing Analytics"),
    ("Meta Ads API",               "api_integration",     "Performance Media"),
    ("Salesforce CRM Connector",   "platform_connection", "Marketing Ops"),
    ("DuckDB Analytics DB",        "database",            "Marketing Analytics"),
    ("Tableau Reporting Suite",    "reporting",           "Marketing Analytics"),
    ("LLM Visibility Tracker",     "other",               "SEO / AEO Team"),
]

# Three snapshots per system: T-48h, T-24h, current
_SNAPSHOT_OFFSETS = [48, 24, 0]  # hours ago

# Base healthy status for all snapshots
_BASE_STATUS = ("healthy", 210, Decimal("99.95"), None, None)

# Overrides for specific (system_name, hours_ago) combos
_HEALTH_OVERRIDES: dict[tuple[str, int], tuple] = {
    # DMP had a degraded state 48h ago
    ("DMP Data Pipeline", 48): (
        "degraded", 4100, Decimal("97.20"),
        "S3 source bucket ACL misconfiguration blocked ingestion for ~2h",
        NOW - timedelta(hours=51),
    ),
    # Meta API rate-limited 48h ago
    ("Meta Ads API", 48): (
        "degraded", 1850, Decimal("98.50"),
        "Rate limit throttle on ad insights endpoint — 429 errors, ~90 min window",
        NOW - timedelta(hours=50),
    ),
    # Tableau had scheduled maintenance 24h ago
    ("Tableau Reporting Suite", 24): (
        "maintenance", None, Decimal("99.50"),
        "Scheduled Tableau Server upgrade v2024.1 → v2024.3",
        NOW - timedelta(hours=26),
    ),
}

# Response time profiles per system (base ms, jitter range)
_RT_PROFILES: dict[str, tuple[int, int]] = {
    "DMP Data Pipeline":       (0, 0),       # N/A for pipeline
    "Meta Ads API":            (195, 40),
    "Salesforce CRM Connector":(480, 60),
    "DuckDB Analytics DB":     (18, 10),
    "Tableau Reporting Suite":  (415, 50),
    "LLM Visibility Tracker":  (740, 80),
}


def _build_system_health() -> pd.DataFrame:
    rows = []
    for sys_name, category, owner_team in _SYSTEMS:
        base_ms, jitter = _RT_PROFILES[sys_name]
        for hours_ago in _SNAPSHOT_OFFSETS:
            override = _HEALTH_OVERRIDES.get((sys_name, hours_ago))
            if override:
                status, resp_ms, uptime, error_msg, last_incident = override
            else:
                status = "healthy"
                resp_ms = (base_ms + int(rng.integers(-jitter // 2, jitter))) if base_ms else None
                uptime = Decimal("99.95")
                error_msg = None
                last_incident = None

            rows.append({
                "id":               str(uuid.uuid4()),
                "system_name":      sys_name,
                "category":         category,
                "status":           status,
                "checked_at":       NOW - timedelta(hours=hours_ago),
                "response_time_ms": resp_ms,
                "uptime_pct":       uptime,
                "error_message":    error_msg,
                "owner_team":       owner_team,
                "last_incident_at": last_incident,
                "created_at":       NOW - timedelta(hours=hours_ago + 1),
                "updated_at":       NOW - timedelta(hours=hours_ago),
            })
    return pd.DataFrame(rows)


HEALTH_SCHEMA = DataFrameSchema(
    {
        "id":          Column(str),
        "system_name": Column(str, Check(lambda s: s.str.len() > 0)),
        "category":    Column(str, Check.isin([
            "data_pipeline", "api_integration", "platform_connection",
            "database", "reporting", "other",
        ])),
        "status":      Column(str, Check.isin([
            "healthy", "degraded", "down", "maintenance", "unknown",
        ])),
        "checked_at":  Column("datetime64[ns]"),
    },
    coerce=True,
)


# ---------------------------------------------------------------------------
# 4. Competitive Intel Items  (20 items)
# ---------------------------------------------------------------------------
# Distribution: 5 competitors × 4 categories each (rough), all 6 categories covered
# Impact mix: critical(1), high(5), medium(10), low(4)

_COMPETITIVE_INTEL_RAW: list[tuple] = [
    # (competitor, category, impact, headline, detail,
    #  observed_date, product_affected, rate_delta_bps,
    #  response_recommended, is_actioned)
    (
        "JPMorgan Chase", "rate_change", "critical",
        "Chase raises HYSA to 5.10% APY — 25 bps above market",
        "Chase Savings Plus now at 5.10%, directly targeting digital-first savers. Paired with heavy SEM conquest.",
        _d(2026, 5, 5), "savings", 25,
        "Evaluate rate match on HYSA; pivot savings campaign to UX differentiation if rate gap holds.",
        False,
    ),
    (
        "JPMorgan Chase", "marketing_campaign", "high",
        "Chase 'Total Checking Bonus' — $300 sign-on for direct deposit",
        "Direct mail + digital push targeting switchers. Offer expires June 30. Heavy Google Search conquest on competitor brands.",
        _d(2026, 4, 18), "checking", None,
        "Consider comparable switching incentive; increase branded SEM bids to defend against conquest traffic.",
        True,
    ),
    (
        "JPMorgan Chase", "product_launch", "high",
        "Chase expands BNPL 'Pay Over Time' to checking debit customers",
        "BNPL on debit transactions over $100. Targets non-credit card holders. Announced with $20M awareness push.",
        _d(2026, 3, 10), "checking", None,
        "Brief product team on debit-linked installment gap. BNPL as retention feature for Gen Z segment.",
        True,
    ),
    (
        "JPMorgan Chase", "regulatory", "medium",
        "Chase settles CFPB inquiry on deceptive overdraft marketing — $95M",
        "Settlement requires Chase to revamp OD fee disclosures and pause certain overdraft promotions.",
        _d(2026, 3, 27), "checking", None,
        "Review our own overdraft marketing language for compliance exposure; brief Legal.",
        True,
    ),
    (
        "Bank of America", "product_launch", "high",
        "BofA launches AI Financial Coach in mobile for 20M+ checking customers",
        "Spending insights, budget goals, predictive savings nudges. Rolling out Q2. Internal ML model.",
        _d(2026, 5, 2), "checking", None,
        "Benchmark against our PFM roadmap. Accelerate personalization feature backlog.",
        False,
    ),
    (
        "Bank of America", "rate_change", "medium",
        "BofA raises mortgage rates +12 bps across 30-year fixed products",
        "BofA now at 7.12% on 30y fixed — above our posted rate. Spring homebuying season opportunity.",
        _d(2026, 4, 15), "mortgage", 12,
        "Promote our mortgage rate competitiveness in spring campaign creative and SEM ad copy.",
        False,
    ),
    (
        "Bank of America", "branch_expansion", "low",
        "BofA pilots cashierless branch format in 5 Texas markets",
        "Fully digital self-service branches with remote teller video. Testing efficiency model for 2027 rollout.",
        _d(2026, 3, 24), "checking", None,
        "Track pilot outcomes. No near-term competitive threat; file for branch strategy awareness.",
        False,
    ),
    (
        "Bank of America", "regulatory", "high",
        "CFPB issues guidance on AI-generated marketing disclosures — BofA as pilot partner",
        "BofA collaborating with CFPB on best practices for AI-personalized offer disclosures. May set industry precedent.",
        _d(2026, 3, 6), None, None,
        "Brief Legal and Compliance on AI marketing disclosure risk. Audit our AI personalization usage.",
        False,
    ),
    (
        "Wells Fargo", "marketing_campaign", "high",
        "Wells Fargo 'Back to Banking' brand refresh — $80M estimated spend",
        "Nationwide brand campaign emphasizing trust and community reinvention. Heavy CTV, OOH, podcast.",
        _d(2026, 4, 28), "checking", None,
        "Monitor brand health scores in overlapping DMAs. Consider defensive brand spend in top 5 markets.",
        True,
    ),
    (
        "Wells Fargo", "product_launch", "medium",
        "Wells Fargo introduces 'Flex Savings' — no-penalty CD with 30-day liquidity",
        "Targets rate-sensitive customers who want HYSA-like liquidity at term-rate yields. Available in 45 states.",
        _d(2026, 4, 10), "savings", None,
        "Brief product marketing on savings differentiation. Assess product positioning gap.",
        False,
    ),
    (
        "Wells Fargo", "rate_change", "medium",
        "Wells Fargo raises Premier Checking relationship rate — HYSA to 4.95%",
        "Relationship pricing tied to total deposits ≥$50K. Defensive play to retain high-balance customers.",
        _d(2026, 3, 20), "savings", 10,
        "Consider relationship pricing tier evaluation for our high-balance checking segment.",
        False,
    ),
    (
        "Wells Fargo", "partnership", "medium",
        "Wells Fargo partners with Intuit TurboTax for refund direct deposit bonus",
        "Tax season promo: $100 bonus routing refund to new WF account. Pushed in TurboTax checkout — est. 5M impressions.",
        _d(2026, 3, 3), "checking", None,
        "Evaluate tax-season direct deposit acquisition play for 2027 marketing planning.",
        True,
    ),
    (
        "U.S. Bank", "rate_change", "medium",
        "U.S. Bank drops 12-month CD rate by 15 bps to 4.65% APY",
        "Rate reduction signals internal funding cost management. Opportunity to lead on CD rates in shared Midwest markets.",
        _d(2026, 5, 1), "cd", -15,
        "Flag to product team — capture CD rate-shoppers in Midwest markets with targeted SEM.",
        False,
    ),
    (
        "U.S. Bank", "marketing_campaign", "medium",
        "U.S. Bank launches SMB checking bundle with $500 new account bonus",
        "Targeting SMB segment with 0-fee business checking. LinkedIn and local radio in Midwest markets.",
        _d(2026, 4, 7), "business_checking", None,
        "Align our SMB campaign brief to counter — ensure bonus offer is visible in shared markets.",
        False,
    ),
    (
        "U.S. Bank", "product_launch", "low",
        "U.S. Bank launches bi-weekly pay splitting feature in mobile app",
        "Auto-splits each paycheck into checking + savings at user-defined ratios. Targets paycheck-to-paycheck consumers.",
        _d(2026, 3, 17), "savings", None,
        "Brief digital banking PM team. Assess auto-savings feature roadmap priority.",
        False,
    ),
    (
        "U.S. Bank", "rate_change", "low",
        "U.S. Bank raises money market rate +8 bps to 4.55% APY",
        "Small rate bump driven by local competitor pressure in Midwest. Below market leaders.",
        _d(2026, 5, 6), "savings", 8,
        "No immediate action. Monitor for continued upward rate movement.",
        False,
    ),
    (
        "Huntington Bank", "branch_expansion", "medium",
        "Huntington announces 18 new branch openings in Columbus and Cincinnati metros",
        "Expansion in underbanked suburban corridors. Accompanied by $10M local marketing push.",
        _d(2026, 4, 22), "checking", None,
        "Review branch density in affected DMAs. Boost SEM coverage in adjacent zip codes.",
        False,
    ),
    (
        "Huntington Bank", "partnership", "low",
        "Huntington partners with DoorDash for instant pay checking promotion",
        "Embedded finance play targeting gig workers. DoorDash co-marketing includes in-app checking offer.",
        _d(2026, 4, 3), "checking", None,
        "Monitor gig economy banking segment. Evaluate embedded distribution opportunities.",
        False,
    ),
    (
        "Huntington Bank", "marketing_campaign", "low",
        "Huntington runs 'Spring Cleaning for Your Finances' digital content campaign",
        "12-part content series across YouTube, TikTok, email. Soft lead gen for checking and savings.",
        _d(2026, 3, 14), "checking", None,
        "Benchmark content engagement. Consider similar awareness-funnel content calendar.",
        False,
    ),
    (
        "Huntington Bank", "rate_change", "medium",
        "Huntington drops auto loan rate to 6.49% for prime borrowers",
        "Promotional rate for conquest auto loans in Ohio and Michigan. Dealer finance marketing push.",
        _d(2026, 5, 3), "auto_loan", -20,
        "Review our auto loan rates in shared Midwest markets. Brief consumer lending on competitive positioning.",
        False,
    ),
]


def _build_competitive_intel() -> pd.DataFrame:
    rows = []
    for (
        competitor, category, impact, headline, detail,
        observed_date, product_affected, rate_delta_bps,
        response_recommended, is_actioned
    ) in _COMPETITIVE_INTEL_RAW:
        rows.append({
            "id":                   str(uuid.uuid4()),
            "competitor_name":      competitor,
            "category":             category,
            "impact":               impact,
            "headline":             headline,
            "detail":               detail,
            "source_url":           None,
            "observed_date":        observed_date,
            "product_affected":     product_affected,
            "rate_delta_bps":       rate_delta_bps,
            "response_recommended": response_recommended,
            "is_actioned":          is_actioned,
            "created_at":           NOW - timedelta(days=int(rng.integers(0, 5))),
            "updated_at":           NOW,
        })
    return pd.DataFrame(rows)


INTEL_SCHEMA = DataFrameSchema(
    {
        "id":              Column(str),
        "competitor_name": Column(str, Check(lambda s: s.str.len() > 0)),
        "category":        Column(str, Check.isin([
            "rate_change", "product_launch", "marketing_campaign",
            "branch_expansion", "partnership", "regulatory", "other",
        ])),
        "impact":          Column(str, Check.isin(["low", "medium", "high", "critical"])),
        "headline":        Column(str, Check(lambda s: s.str.len() > 0)),
        "observed_date":   Column("datetime64[ns]"),
    },
    coerce=True,
)


# ---------------------------------------------------------------------------
# 5. Team Capacity  (96 rows: 8 teams × 12 monthly periods 2025-06 → 2026-05)
# ---------------------------------------------------------------------------

_TEAMS = [
    # (team_name, function, base_headcount_total, base_headcount_fte, base_open_reqs)
    ("Brand Strategy",      "brand",               6, 5, 1),
    ("Performance Media",   "performance_media",   9, 7, 2),
    ("SEO & Content",       "seo_content",         5, 4, 1),
    ("Marketing Analytics", "analytics",           7, 6, 1),
    ("Creative Studio",     "creative",            8, 6, 2),
    ("Product Marketing",   "product_marketing",   5, 5, 0),
    ("Marketing Ops",       "ops",                 4, 4, 1),
    ("MarTech & Data",      "other",               6, 5, 1),
]

_PERIODS_12 = TWELVE_MONTH_STRINGS

# Base utilization percentage by team
_UTIL_BASE = {
    "Brand Strategy":      82.0,
    "Performance Media":   91.0,
    "SEO & Content":       78.0,
    "Marketing Analytics": 88.0,
    "Creative Studio":     85.0,
    "Product Marketing":   79.0,
    "Marketing Ops":       75.0,
    "MarTech & Data":      83.0,
}

# Month-level seasonal multipliers (Q1/Q2 high, summer lower, Dec low)
_MONTH_MULT = {
    "01": 1.05, "02": 1.03, "03": 1.08, "04": 1.06, "05": 1.04,
    "06": 0.95, "07": 0.93, "08": 0.96, "09": 1.00, "10": 1.02,
    "11": 1.04, "12": 0.90,
}

_HOURS_PER_PERSON_MONTH = 160


def _build_team_capacity() -> pd.DataFrame:
    rows = []
    for team_name, function, base_hc_total, base_hc_fte, base_open_reqs in _TEAMS:
        base_util = _UTIL_BASE[team_name]
        for period in _PERIODS_12:
            month = period.split("-")[1]
            multiplier = _MONTH_MULT[month]
            util = float(min(98.0, base_util * multiplier + rng.uniform(-1.5, 1.5)))
            util = round(util, 2)

            hc_total = max(1, base_hc_total + int(rng.integers(-1, 2)))
            hc_fte = min(base_hc_fte, hc_total)
            open_reqs = max(0, base_open_reqs + int(rng.integers(-1, 2)))
            avail_hrs = max(0, int(hc_total * _HOURS_PER_PERSON_MONTH * (1.0 - util / 100.0)))

            rows.append({
                "id":                    str(uuid.uuid4()),
                "team_name":             team_name,
                "function":              function,
                "period":                period,
                "headcount_total":       hc_total,
                "headcount_fte":         hc_fte,
                "open_reqs":             open_reqs,
                "utilization_pct":       Decimal(str(util)),
                "capacity_available_hrs": avail_hrs,
                "notes":                 None,
                "created_at":            NOW,
                "updated_at":            NOW,
            })
    return pd.DataFrame(rows)


CAPACITY_SCHEMA = DataFrameSchema(
    {
        "id":              Column(str),
        "team_name":       Column(str, Check(lambda s: s.str.len() > 0)),
        "function":        Column(str, Check.isin([
            "brand", "performance_media", "seo_content", "analytics",
            "creative", "product_marketing", "ops", "other",
        ])),
        "period":          Column(str, Check(lambda s: s.str.match(r"^\d{4}-\d{2}$"))),
        "headcount_total": Column(int, Check.ge(1)),
        "headcount_fte":   Column(int, Check.ge(1)),
        "utilization_pct": Column(float, [Check.ge(0.0), Check.le(100.0)]),
    },
    coerce=True,
)


# ---------------------------------------------------------------------------
# DB persistence helper
# ---------------------------------------------------------------------------

def _upsert(conn, table: str, df: pd.DataFrame, reg: str, cols: list[str]) -> None:
    conn.execute(f"DELETE FROM {table}")
    conn.register(reg, df)
    col_list = ", ".join(f'"{c}"' for c in cols)
    conn.execute(f"INSERT INTO {table} ({col_list}) SELECT {col_list} FROM {reg}")
    try:
        conn.unregister(reg)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public seed entry point
# ---------------------------------------------------------------------------

def seed(verbose: bool = True) -> dict[str, pd.DataFrame]:
    """Build, validate, and persist all 5 ops datasets. Returns dict of DataFrames."""
    cal_df = _build_calendar_events()
    appr_df = _build_approval_items()
    health_df = _build_system_health()
    intel_df = _build_competitive_intel()
    cap_df = _build_team_capacity()

    # --- Acceptance-criteria assertions ---
    assert len(cal_df) >= 30, f"calendar_events: {len(cal_df)} < 30"
    pending_count = (appr_df["status"] == "pending").sum()
    assert pending_count >= 10, f"pending approvals: {pending_count} < 10"
    assert len(appr_df[appr_df["budget_impact"].notna()]) == len(appr_df), \
        "all approval_items must have a budget_impact value"
    sys_cats = health_df["category"].nunique()
    assert sys_cats == 6, f"health_checks covers {sys_cats} categories (need 6)"
    assert len(health_df) >= 15, f"system_health_checks: {len(health_df)} < 15"
    assert len(intel_df) >= 20, f"competitive_intel_items: {len(intel_df)} < 20"
    assert len(cap_df) == 96, f"team_capacity: {len(cap_df)} != 96"

    # --- Pandera schema validation ---
    CALENDAR_SCHEMA.validate(cal_df)
    APPROVAL_SCHEMA.validate(appr_df)
    HEALTH_SCHEMA.validate(health_df)
    INTEL_SCHEMA.validate(intel_df)
    CAPACITY_SCHEMA.validate(cap_df)

    conn = get_connection()
    try:
        _upsert(conn, "calendar_events", cal_df, "_cal", [
            "id", "title", "event_type", "status", "start_dt", "end_dt",
            "owner", "attendees", "description", "related_campaign_id",
            "created_at", "updated_at",
        ])
        _upsert(conn, "approval_items", appr_df, "_appr", [
            "id", "title", "category", "status", "priority",
            "requestor", "approver", "due_date", "resolved_at",
            "budget_impact", "notes", "artifact_url",
            "created_at", "updated_at",
        ])
        _upsert(conn, "system_health_checks", health_df, "_health", [
            "id", "system_name", "category", "status", "checked_at",
            "response_time_ms", "uptime_pct", "error_message",
            "owner_team", "last_incident_at",
            "created_at", "updated_at",
        ])
        _upsert(conn, "competitive_intel_items", intel_df, "_intel", [
            "id", "competitor_name", "category", "impact", "headline",
            "detail", "source_url", "observed_date", "product_affected",
            "rate_delta_bps", "response_recommended", "is_actioned",
            "created_at", "updated_at",
        ])
        _upsert(conn, "team_capacity", cap_df, "_cap", [
            "id", "team_name", "function", "period",
            "headcount_total", "headcount_fte", "open_reqs",
            "utilization_pct", "capacity_available_hrs", "notes",
            "created_at", "updated_at",
        ])
        conn.commit()
    finally:
        conn.close()

    if verbose:
        print(f"[seed_ops] calendar_events:         {len(cal_df)} rows "
              f"(types: {cal_df['event_type'].nunique()})")
        print(f"[seed_ops] approval_items:          {len(appr_df)} rows "
              f"({pending_count} pending)")
        print(f"[seed_ops] system_health_checks:    {len(health_df)} rows "
              f"({health_df['category'].nunique()} categories)")
        print(f"[seed_ops] competitive_intel_items: {len(intel_df)} rows "
              f"({intel_df['competitor_name'].nunique()} competitors)")
        print(f"[seed_ops] team_capacity:           {len(cap_df)} rows "
              f"({cap_df['team_name'].nunique()} teams × {cap_df['period'].nunique()} periods)")

    return {
        "calendar_events":         cal_df,
        "approval_items":          appr_df,
        "system_health_checks":    health_df,
        "competitive_intel_items": intel_df,
        "team_capacity":           cap_df,
    }


if __name__ == "__main__":
    dfs = seed(verbose=True)
    total = sum(len(v) for v in dfs.values())
    print(f"\nOps seed complete: {total} total rows across {len(dfs)} tables")
