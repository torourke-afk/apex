"""Audit REST API — compliance & QA scanning.

GET  /api/audit/reports          — list recent audit reports
GET  /api/audit/reports/{id}     — single report with all findings
POST /api/audit/scan             — trigger a new scan
GET  /api/audit/rules            — list registered compliance rules
GET  /api/audit/summary          — aggregate stats
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.services.audit import (
    RULES,
    AuditReport as AuditReportDC,
    ComplianceFinding as ComplianceFindingDC,
    QAResult as QAResultDC,
    get_seed_reports,
    run_compliance_scan,
    run_full_scan,
    run_qa_scan,
)

router = APIRouter(prefix="/api/audit", tags=["audit"])


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------

class ComplianceFindingOut(BaseModel):
    rule_id: str
    rule_name: str
    category: str
    severity: str
    verdict: str
    evidence: str


class QAResultOut(BaseModel):
    dimension: str
    score: float
    details: str


class AuditReportOut(BaseModel):
    id: str
    target_url: str
    created_at: str
    scan_type: str
    compliance_results: list[ComplianceFindingOut]
    qa_results: list[QAResultOut]
    overall_score: float
    pass_count: int
    warn_count: int
    fail_count: int


class AuditReportListResponse(BaseModel):
    items: list[AuditReportOut]
    total: int


class ScanRequest(BaseModel):
    target_url: str
    scan_type: str = "full"  # compliance | qa | full


class RuleOut(BaseModel):
    id: str
    name: str
    category: str
    severity: str
    description: str


class RulesListResponse(BaseModel):
    rules: list[RuleOut]
    total: int


class AuditSummaryResponse(BaseModel):
    total_scans: int
    avg_score: float
    common_failures: list[dict]
    by_category: dict[str, dict]
    as_of: str


# ---------------------------------------------------------------------------
# In-memory report store (seed + runtime)
# ---------------------------------------------------------------------------

_reports: list[AuditReportDC] = []
_initialized: bool = False


def _ensure_seed() -> None:
    global _initialized
    if not _initialized:
        _reports.extend(get_seed_reports())
        _initialized = True


def _dc_to_pydantic(r: AuditReportDC) -> AuditReportOut:
    return AuditReportOut(
        id=r.id,
        target_url=r.target_url,
        created_at=r.created_at,
        scan_type=r.scan_type,
        compliance_results=[
            ComplianceFindingOut(
                rule_id=f.rule_id,
                rule_name=f.rule_name,
                category=f.category,
                severity=f.severity,
                verdict=f.verdict,
                evidence=f.evidence,
            )
            for f in r.compliance_results
        ],
        qa_results=[
            QAResultOut(dimension=q.dimension, score=q.score, details=q.details)
            for q in r.qa_results
        ],
        overall_score=r.overall_score,
        pass_count=r.pass_count,
        warn_count=r.warn_count,
        fail_count=r.fail_count,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/reports", response_model=AuditReportListResponse)
def list_reports(
    scan_type: Optional[str] = Query(
        default=None,
        description="Filter by scan type: compliance | qa | full",
    ),
    limit: int = Query(default=20, ge=1, le=100),
) -> AuditReportListResponse:
    """List recent audit reports, newest first."""
    _ensure_seed()
    items = list(reversed(_reports))  # newest first
    if scan_type:
        items = [r for r in items if r.scan_type == scan_type]
    items = items[:limit]
    return AuditReportListResponse(
        items=[_dc_to_pydantic(r) for r in items],
        total=len(items),
    )


@router.get("/reports/{report_id}", response_model=AuditReportOut)
def get_report(report_id: str) -> AuditReportOut:
    """Retrieve a single audit report by ID."""
    _ensure_seed()
    for r in _reports:
        if r.id == report_id:
            return _dc_to_pydantic(r)
    raise HTTPException(status_code=404, detail=f"Audit report '{report_id}' not found.")


@router.post("/scan", response_model=AuditReportOut)
def trigger_scan(body: ScanRequest) -> AuditReportOut:
    """Trigger a new compliance / QA / full scan.

    In production the scan would fetch and parse *target_url*.  For the
    seed/demo layer we run the engine against a representative HTML
    snippet so the rule engine is exercised end-to-end.
    """
    _ensure_seed()

    # Representative HTML snippet for demo — in production this would be
    # the fetched page content.
    _DEMO_CONTENT = """
    <html>
    <head>
        <script type="application/ld+json">{"@context":"https://schema.org","@type":"BankOrCreditUnion","name":"Fifth Third Bank"}</script>
    </head>
    <body>
        <h1>Open a Checking Account</h1>
        <h2>Earn a $250 bonus</h2>
        <p>Enjoy our free checking account with no monthly fees. Terms and conditions apply. See details.</p>
        <p>Earn 4.25% APY on your savings. Interest rate is variable and subject to change.</p>
        <img src="hero.jpg" alt="Happy family banking online">
        <img src="promo.jpg">
        <a href="https://www.fifththird.com/apply">Apply Now</a>
        <a href="#">Learn More</a>
        <form>
            <label for="email">Email</label>
            <input id="email" type="email">
            <input type="text" placeholder="Name">
        </form>
        <h3>Features</h3>
        <footer>
            <p>Member FDIC. Equal Housing Lender.</p>
        </footer>
    </body>
    </html>
    """

    import uuid as _uuid
    from src.services.audit import _compute_overall

    now_iso = datetime.now(timezone.utc).isoformat()

    if body.scan_type == "compliance":
        compliance = run_compliance_scan(_DEMO_CONTENT)
        qa: list[QAResultDC] = []
        overall, pc, wc, fc = _compute_overall(compliance, qa)
        report = AuditReportDC(
            id=str(_uuid.uuid4()),
            target_url=body.target_url,
            created_at=now_iso,
            scan_type="compliance",
            compliance_results=compliance,
            qa_results=qa,
            overall_score=overall,
            pass_count=pc,
            warn_count=wc,
            fail_count=fc,
        )
    elif body.scan_type == "qa":
        compliance_findings: list[ComplianceFindingDC] = []
        qa = run_qa_scan(_DEMO_CONTENT)
        qa_avg = sum(q.score for q in qa) / len(qa) if qa else 100.0
        report = AuditReportDC(
            id=str(_uuid.uuid4()),
            target_url=body.target_url,
            created_at=now_iso,
            scan_type="qa",
            compliance_results=compliance_findings,
            qa_results=qa,
            overall_score=round(qa_avg, 1),
            pass_count=0,
            warn_count=0,
            fail_count=0,
        )
    else:
        report = run_full_scan(body.target_url, _DEMO_CONTENT)

    _reports.append(report)
    return _dc_to_pydantic(report)


@router.get("/rules", response_model=RulesListResponse)
def list_rules(
    category: Optional[str] = Query(
        default=None,
        description="Filter by category: FDIC | EHL | RegDD | UDAAP | Accessibility | OfferTerms",
    ),
) -> RulesListResponse:
    """List all registered compliance rules."""
    items = RULES
    if category:
        items = [r for r in items if r.category.value == category]
    return RulesListResponse(
        rules=[
            RuleOut(
                id=r.id,
                name=r.name,
                category=r.category.value,
                severity=r.severity.value,
                description=r.description,
            )
            for r in items
        ],
        total=len(items),
    )


@router.get("/summary", response_model=AuditSummaryResponse)
def audit_summary() -> AuditSummaryResponse:
    """Aggregate stats across all audit reports."""
    _ensure_seed()

    total_scans = len(_reports)
    avg_score = round(
        sum(r.overall_score for r in _reports) / total_scans, 1
    ) if total_scans else 0.0

    # Count failures by rule_id across all reports
    failure_counts: dict[str, int] = {}
    category_stats: dict[str, dict] = {}

    for report in _reports:
        for f in report.compliance_results:
            cat = f.category
            if cat not in category_stats:
                category_stats[cat] = {"pass": 0, "warn": 0, "fail": 0}
            category_stats[cat][f.verdict] = category_stats[cat].get(f.verdict, 0) + 1

            if f.verdict == "fail":
                key = f"{f.rule_id}: {f.rule_name}"
                failure_counts[key] = failure_counts.get(key, 0) + 1

    common_failures = sorted(
        [{"rule": k, "count": v} for k, v in failure_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:10]

    return AuditSummaryResponse(
        total_scans=total_scans,
        avg_score=avg_score,
        common_failures=common_failures,
        by_category=category_stats,
        as_of=datetime.now(timezone.utc).isoformat(),
    )
