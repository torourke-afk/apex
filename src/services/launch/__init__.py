"""Launch / Site Factory Service (#13).

Implements the recommendation-to-ticket-to-proof-to-build-to-launch pipeline
with human gates.  This is the Conversion pillar's "Site Factory" — an
operator-paced pipeline where each stage runs or awaits, then the operator
advances.  Interactive human gates enforce governance before launch.

Pipeline stages:
    RECOMMENDATION -> TICKETS -> PROOFING -> FACTORY -> PREVIEW
    -> COMPLIANCE -> QA -> APPROVE -> EXPERIMENT -> LAUNCHED
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------

class PipelineStage(str, Enum):
    """Ordered stages in the launch pipeline."""

    RECOMMENDATION = "RECOMMENDATION"
    TICKETS = "TICKETS"
    PROOFING = "PROOFING"
    FACTORY = "FACTORY"
    PREVIEW = "PREVIEW"
    COMPLIANCE = "COMPLIANCE"
    QA = "QA"
    APPROVE = "APPROVE"
    EXPERIMENT = "EXPERIMENT"
    LAUNCHED = "LAUNCHED"


# Ordered list for advancement logic.
STAGE_ORDER: list[PipelineStage] = list(PipelineStage)

# Stages that require explicit human approval before advancing.
HUMAN_GATES: set[PipelineStage] = {PipelineStage.APPROVE}


class StageStatus(str, Enum):
    """Status of an individual pipeline stage."""

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    SKIPPED = "skipped"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class StageRecord(BaseModel):
    """Tracks a single stage within a proposal's pipeline."""

    stage: PipelineStage
    status: StageStatus = StageStatus.PENDING
    entered_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None


class ContentBlock(BaseModel):
    """A discrete content section within a landing-page spec."""

    block_type: str = Field(description="e.g. hero, features, testimonial, cta, faq, disclosure")
    heading: Optional[str] = None
    body: Optional[str] = None
    cta_label: Optional[str] = None
    cta_url: Optional[str] = None


class SiteSpec(BaseModel):
    """Generated landing-page specification for a launch proposal."""

    title: str
    hero_headline: str
    hero_subheadline: Optional[str] = None
    cta_label: str
    cta_url: str
    offer_terms: Optional[str] = None
    routes: list[str] = Field(default_factory=list)
    content_blocks: list[ContentBlock] = Field(default_factory=list)
    schema_org_type: str = "FinancialProduct"
    disclosure_requirements: list[str] = Field(default_factory=list)


class ComplianceResult(BaseModel):
    """Result of the compliance scan stage."""

    passed: bool
    checks: list[dict] = Field(default_factory=list)
    scanned_at: Optional[datetime] = None


class QAResult(BaseModel):
    """Result of the QA scan stage."""

    score: float = Field(ge=0, le=100, description="Lighthouse-ish composite score")
    checks: list[dict] = Field(default_factory=list)
    scanned_at: Optional[datetime] = None


class ProposalStatus(str, Enum):
    """High-level status of the launch proposal."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class LaunchProposal(BaseModel):
    """A single launch-pipeline proposal moving through all stages."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str
    persona: str
    product: str
    status: ProposalStatus = ProposalStatus.ACTIVE
    current_stage: PipelineStage = PipelineStage.RECOMMENDATION
    stages: list[StageRecord] = Field(default_factory=list)
    site_spec: Optional[SiteSpec] = None
    compliance_results: Optional[ComplianceResult] = None
    qa_results: Optional[QAResult] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Stage advancement logic
# ---------------------------------------------------------------------------

class StageAdvanceError(Exception):
    """Raised when a stage cannot be advanced."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _init_stages(start: PipelineStage = PipelineStage.RECOMMENDATION) -> list[StageRecord]:
    """Build the full stage list, marking the start stage as active."""
    records: list[StageRecord] = []
    for stage in STAGE_ORDER:
        if stage == start:
            records.append(StageRecord(stage=stage, status=StageStatus.ACTIVE, entered_at=_now()))
        else:
            records.append(StageRecord(stage=stage, status=StageStatus.PENDING))
    return records


def advance_stage(
    proposal: LaunchProposal,
    *,
    gate_approved: bool = False,
) -> LaunchProposal:
    """Advance *proposal* to its next pipeline stage.

    Parameters
    ----------
    proposal:
        The proposal to advance.  Mutated in place and returned.
    gate_approved:
        Must be ``True`` when the current stage is a human gate
        (currently only APPROVE).

    Raises
    ------
    StageAdvanceError
        If the proposal is already launched, cancelled, or at a human gate
        without approval.
    """
    if proposal.status != ProposalStatus.ACTIVE:
        raise StageAdvanceError(
            f"Proposal '{proposal.name}' has status {proposal.status.value}; "
            "only active proposals can advance."
        )

    current_idx = STAGE_ORDER.index(proposal.current_stage)

    if current_idx >= len(STAGE_ORDER) - 1:
        raise StageAdvanceError(
            f"Proposal '{proposal.name}' is already at the final stage "
            f"({proposal.current_stage.value})."
        )

    # Human gate check.
    if proposal.current_stage in HUMAN_GATES and not gate_approved:
        raise StageAdvanceError(
            f"Stage {proposal.current_stage.value} is a human gate — "
            "explicit approval is required (pass gate_approved=True)."
        )

    now = _now()

    # Complete current stage.
    for rec in proposal.stages:
        if rec.stage == proposal.current_stage:
            rec.status = StageStatus.COMPLETED
            rec.completed_at = now
            break

    # Activate next stage.
    next_stage = STAGE_ORDER[current_idx + 1]
    for rec in proposal.stages:
        if rec.stage == next_stage:
            rec.status = StageStatus.ACTIVE
            rec.entered_at = now
            break

    proposal.current_stage = next_stage
    proposal.updated_at = now

    # If we just moved to LAUNCHED, mark the proposal completed.
    if next_stage == PipelineStage.LAUNCHED:
        proposal.status = ProposalStatus.COMPLETED
        for rec in proposal.stages:
            if rec.stage == PipelineStage.LAUNCHED:
                rec.status = StageStatus.COMPLETED
                rec.completed_at = now
                break

    return proposal


# ---------------------------------------------------------------------------
# Site-spec generation
# ---------------------------------------------------------------------------

_PERSONA_HEADLINES: dict[str, str] = {
    "young-professional": "Your Money, Your Momentum",
    "new-mover": "New City. New Bank. No Hassle.",
    "small-business": "Business Banking That Works as Hard as You Do",
    "retiree": "A Smarter Way to Manage Your Retirement Accounts",
    "college-student": "Banking Built for Campus Life",
}

_PRODUCT_OFFERS: dict[str, dict] = {
    "momentum-checking": {
        "cta_label": "Open Momentum Checking",
        "offer_terms": (
            "Earn $350 bonus when you open a new Fifth Third Momentum Checking "
            "account with qualifying direct deposits within 90 days. "
            "Offer valid for new checking customers only."
        ),
        "schema_org_type": "FinancialProduct",
        "disclosures": [
            "Member FDIC",
            "Equal Housing Lender",
            "Bonus reported as interest income on IRS Form 1099-INT",
            "See full offer terms and conditions at 53.com/offer-terms",
        ],
    },
    "express-savings": {
        "cta_label": "Open Express Savings",
        "offer_terms": (
            "Earn 4.75% APY on balances up to $25,000 with Fifth Third "
            "Express Savings. No minimum balance required."
        ),
        "schema_org_type": "FinancialProduct",
        "disclosures": [
            "Member FDIC",
            "Equal Housing Lender",
            "APY accurate as of 07/01/2026. Rate subject to change.",
            "Reg DD: Fees may reduce earnings on the account.",
        ],
    },
    "auto-loan": {
        "cta_label": "Get Pre-Qualified",
        "offer_terms": (
            "Rates as low as 5.49% APR on new auto loans. "
            "Pre-qualify in minutes with no impact to your credit score."
        ),
        "schema_org_type": "FinancialProduct",
        "disclosures": [
            "Member FDIC",
            "Equal Housing Lender",
            "Rate based on creditworthiness and loan term. Not all applicants will qualify.",
        ],
    },
}


def generate_site_spec(persona: str, product: str, name: str) -> SiteSpec:
    """Generate a landing-page specification from persona + product.

    Returns a deterministic spec for known persona/product combos and a
    sensible default for unknown ones.
    """
    headline = _PERSONA_HEADLINES.get(persona, "Smarter Banking Starts Here")
    product_info = _PRODUCT_OFFERS.get(product, _PRODUCT_OFFERS["momentum-checking"])

    slug = name.lower().replace(" ", "-").replace("'", "")
    routes = [
        f"/offers/{slug}",
        f"/offers/{slug}/terms",
        f"/offers/{slug}/apply",
    ]

    content_blocks = [
        ContentBlock(
            block_type="hero",
            heading=headline,
            body=(
                f"Tailored for the {persona.replace('-', ' ')} in you. "
                "Open your account today and start earning."
            ),
            cta_label=product_info["cta_label"],
            cta_url=routes[2] if routes else "/apply",
        ),
        ContentBlock(
            block_type="features",
            heading="Why Choose Fifth Third?",
            body=(
                "No monthly fees with qualifying activity. "
                "Mobile banking rated #1 by J.D. Power. "
                "1,100+ branches and 2,400+ ATMs."
            ),
        ),
        ContentBlock(
            block_type="offer-terms",
            heading="Offer Details",
            body=product_info["offer_terms"],
        ),
        ContentBlock(
            block_type="disclosure",
            heading="Important Disclosures",
            body=" | ".join(product_info["disclosures"]),
        ),
        ContentBlock(
            block_type="cta",
            heading="Ready to Get Started?",
            cta_label=product_info["cta_label"],
            cta_url=routes[2] if routes else "/apply",
        ),
    ]

    return SiteSpec(
        title=f"{name} | Fifth Third Bank",
        hero_headline=headline,
        hero_subheadline=(
            f"A {product.replace('-', ' ')} experience designed for "
            f"{persona.replace('-', ' ')}s."
        ),
        cta_label=product_info["cta_label"],
        cta_url=routes[2] if routes else "/apply",
        offer_terms=product_info["offer_terms"],
        routes=routes,
        content_blocks=content_blocks,
        schema_org_type=product_info["schema_org_type"],
        disclosure_requirements=product_info["disclosures"],
    )


# ---------------------------------------------------------------------------
# Seed data — 5 proposals at various pipeline stages
# ---------------------------------------------------------------------------

def _seed_proposals() -> list[LaunchProposal]:
    """Return 5 sample launch proposals at different pipeline stages."""
    now = _now()
    proposals: list[LaunchProposal] = []

    # Helper to build stages with some completed.
    def _make_stages(completed_through_idx: int) -> list[StageRecord]:
        records: list[StageRecord] = []
        for i, stage in enumerate(STAGE_ORDER):
            if i < completed_through_idx:
                records.append(StageRecord(
                    stage=stage,
                    status=StageStatus.COMPLETED,
                    entered_at=now - timedelta(days=20 - i * 2),
                    completed_at=now - timedelta(days=19 - i * 2),
                ))
            elif i == completed_through_idx:
                records.append(StageRecord(
                    stage=stage,
                    status=StageStatus.ACTIVE,
                    entered_at=now - timedelta(hours=6),
                ))
            else:
                records.append(StageRecord(stage=stage, status=StageStatus.PENDING))
        return records

    # 1. Early stage — still in TICKETS
    p1 = LaunchProposal(
        id="launch-001",
        name="Momentum Checking — Young Professionals",
        persona="young-professional",
        product="momentum-checking",
        status=ProposalStatus.ACTIVE,
        current_stage=PipelineStage.TICKETS,
        stages=_make_stages(1),
        site_spec=generate_site_spec(
            "young-professional", "momentum-checking",
            "Momentum Checking — Young Professionals",
        ),
        created_at=now - timedelta(days=18),
        updated_at=now - timedelta(hours=6),
    )
    proposals.append(p1)

    # 2. Mid-pipeline — in FACTORY (building the site)
    p2 = LaunchProposal(
        id="launch-002",
        name="Express Savings — New Movers",
        persona="new-mover",
        product="express-savings",
        status=ProposalStatus.ACTIVE,
        current_stage=PipelineStage.FACTORY,
        stages=_make_stages(3),
        site_spec=generate_site_spec(
            "new-mover", "express-savings",
            "Express Savings — New Movers",
        ),
        created_at=now - timedelta(days=25),
        updated_at=now - timedelta(hours=3),
    )
    proposals.append(p2)

    # 3. At the human gate — APPROVE
    p3_stages = _make_stages(7)
    p3 = LaunchProposal(
        id="launch-003",
        name="Auto Loan — Small Business",
        persona="small-business",
        product="auto-loan",
        status=ProposalStatus.ACTIVE,
        current_stage=PipelineStage.APPROVE,
        stages=p3_stages,
        site_spec=generate_site_spec(
            "small-business", "auto-loan",
            "Auto Loan — Small Business",
        ),
        compliance_results=ComplianceResult(
            passed=True,
            checks=[
                {"check": "Member FDIC", "status": "pass", "evidence": "Footer text present"},
                {"check": "Equal Housing Lender", "status": "pass", "evidence": "Footer icon + text"},
                {"check": "Offer T&Cs", "status": "pass", "evidence": "Terms page linked from hero CTA"},
                {"check": "UDAAP language", "status": "pass", "evidence": "No prohibited claims found"},
                {"check": "a11y (axe-core)", "status": "pass", "evidence": "0 violations, 3 warnings"},
            ],
            scanned_at=now - timedelta(hours=2),
        ),
        qa_results=QAResult(
            score=94.0,
            checks=[
                {"check": "Performance (LCP)", "status": "pass", "value": "1.2s"},
                {"check": "Offer accuracy", "status": "pass", "value": "Matches source of record"},
                {"check": "CTA link crawl", "status": "pass", "value": "3/3 links valid"},
                {"check": "Schema.org JSON-LD", "status": "pass", "value": "FinancialProduct valid"},
                {"check": "Responsive", "status": "warn", "value": "Minor overflow at 320px"},
            ],
            scanned_at=now - timedelta(hours=1),
        ),
        created_at=now - timedelta(days=30),
        updated_at=now - timedelta(hours=1),
    )
    proposals.append(p3)

    # 4. In EXPERIMENT — A/B test running
    p4 = LaunchProposal(
        id="launch-004",
        name="Momentum Checking — College Students",
        persona="college-student",
        product="momentum-checking",
        status=ProposalStatus.ACTIVE,
        current_stage=PipelineStage.EXPERIMENT,
        stages=_make_stages(8),
        site_spec=generate_site_spec(
            "college-student", "momentum-checking",
            "Momentum Checking — College Students",
        ),
        compliance_results=ComplianceResult(
            passed=True,
            checks=[
                {"check": "Member FDIC", "status": "pass", "evidence": "Present"},
                {"check": "Equal Housing Lender", "status": "pass", "evidence": "Present"},
                {"check": "Offer T&Cs", "status": "pass", "evidence": "Linked"},
                {"check": "UDAAP language", "status": "pass", "evidence": "Clean"},
                {"check": "a11y (axe-core)", "status": "pass", "evidence": "0 violations"},
            ],
            scanned_at=now - timedelta(days=3),
        ),
        qa_results=QAResult(
            score=97.0,
            checks=[
                {"check": "Performance (LCP)", "status": "pass", "value": "0.9s"},
                {"check": "Offer accuracy", "status": "pass", "value": "Match"},
                {"check": "CTA link crawl", "status": "pass", "value": "3/3 valid"},
                {"check": "Schema.org JSON-LD", "status": "pass", "value": "Valid"},
                {"check": "Responsive", "status": "pass", "value": "All breakpoints OK"},
            ],
            scanned_at=now - timedelta(days=3),
        ),
        created_at=now - timedelta(days=40),
        updated_at=now - timedelta(days=1),
    )
    proposals.append(p4)

    # 5. Completed — LAUNCHED
    p5_stages: list[StageRecord] = []
    for i, stage in enumerate(STAGE_ORDER):
        p5_stages.append(StageRecord(
            stage=stage,
            status=StageStatus.COMPLETED,
            entered_at=now - timedelta(days=60 - i * 5),
            completed_at=now - timedelta(days=59 - i * 5),
        ))
    p5 = LaunchProposal(
        id="launch-005",
        name="Express Savings — Retirees",
        persona="retiree",
        product="express-savings",
        status=ProposalStatus.COMPLETED,
        current_stage=PipelineStage.LAUNCHED,
        stages=p5_stages,
        site_spec=generate_site_spec(
            "retiree", "express-savings",
            "Express Savings — Retirees",
        ),
        compliance_results=ComplianceResult(
            passed=True,
            checks=[
                {"check": "Member FDIC", "status": "pass", "evidence": "Present"},
                {"check": "Equal Housing Lender", "status": "pass", "evidence": "Present"},
                {"check": "Reg DD rates", "status": "pass", "evidence": "APY disclosed"},
                {"check": "Offer T&Cs", "status": "pass", "evidence": "Linked"},
                {"check": "UDAAP language", "status": "pass", "evidence": "Clean"},
                {"check": "a11y (axe-core)", "status": "pass", "evidence": "0 violations"},
            ],
            scanned_at=now - timedelta(days=20),
        ),
        qa_results=QAResult(
            score=96.0,
            checks=[
                {"check": "Performance (LCP)", "status": "pass", "value": "1.0s"},
                {"check": "Offer accuracy", "status": "pass", "value": "Match"},
                {"check": "CTA link crawl", "status": "pass", "value": "3/3 valid"},
                {"check": "Schema.org JSON-LD", "status": "pass", "value": "Valid"},
                {"check": "Responsive", "status": "pass", "value": "All breakpoints OK"},
            ],
            scanned_at=now - timedelta(days=20),
        ),
        created_at=now - timedelta(days=60),
        updated_at=now - timedelta(days=15),
    )
    proposals.append(p5)

    return proposals


# ---------------------------------------------------------------------------
# In-memory store (seeded on import)
# ---------------------------------------------------------------------------

_PROPOSALS: dict[str, LaunchProposal] = {}


def _ensure_seeded() -> dict[str, LaunchProposal]:
    """Lazily seed the in-memory store on first access."""
    if not _PROPOSALS:
        for p in _seed_proposals():
            _PROPOSALS[p.id] = p
    return _PROPOSALS


def get_all_proposals() -> list[LaunchProposal]:
    """Return all launch proposals, ordered by created_at desc."""
    store = _ensure_seeded()
    return sorted(store.values(), key=lambda p: p.created_at, reverse=True)


def get_proposal(proposal_id: str) -> Optional[LaunchProposal]:
    """Return a single proposal by ID, or ``None``."""
    store = _ensure_seeded()
    return store.get(proposal_id)


def create_proposal(name: str, persona: str, product: str) -> LaunchProposal:
    """Create a new launch proposal and add it to the store.

    The proposal starts at RECOMMENDATION with a generated site spec.
    """
    store = _ensure_seeded()
    spec = generate_site_spec(persona, product, name)
    proposal = LaunchProposal(
        name=name,
        persona=persona,
        product=product,
        current_stage=PipelineStage.RECOMMENDATION,
        stages=_init_stages(),
        site_spec=spec,
    )
    store[proposal.id] = proposal
    return proposal


def advance_proposal(proposal_id: str, *, gate_approved: bool = False) -> LaunchProposal:
    """Advance a proposal to its next stage.

    Raises
    ------
    KeyError
        If the proposal ID is not found.
    StageAdvanceError
        If the proposal cannot advance (see :func:`advance_stage`).
    """
    store = _ensure_seeded()
    proposal = store.get(proposal_id)
    if proposal is None:
        raise KeyError(f"Proposal '{proposal_id}' not found")
    return advance_stage(proposal, gate_approved=gate_approved)


def get_pipeline_stats() -> dict:
    """Return aggregate pipeline statistics."""
    store = _ensure_seeded()
    proposals = list(store.values())
    total = len(proposals)

    by_stage: dict[str, int] = {}
    for stage in PipelineStage:
        by_stage[stage.value] = 0
    for p in proposals:
        by_stage[p.current_stage.value] += 1

    by_status: dict[str, int] = {}
    for status in ProposalStatus:
        by_status[status.value] = 0
    for p in proposals:
        by_status[p.status.value] += 1

    # Average cycle time for completed proposals (first stage entered -> last stage completed).
    completed = [p for p in proposals if p.status == ProposalStatus.COMPLETED]
    avg_cycle_days: Optional[float] = None
    if completed:
        cycle_times: list[float] = []
        for p in completed:
            first_enter = min(
                (s.entered_at for s in p.stages if s.entered_at is not None),
                default=None,
            )
            last_complete = max(
                (s.completed_at for s in p.stages if s.completed_at is not None),
                default=None,
            )
            if first_enter and last_complete:
                cycle_times.append((last_complete - first_enter).total_seconds() / 86400)
        if cycle_times:
            avg_cycle_days = round(sum(cycle_times) / len(cycle_times), 1)

    return {
        "total": total,
        "by_stage": by_stage,
        "by_status": by_status,
        "avg_cycle_days": avg_cycle_days,
        "active": by_status.get("active", 0),
        "completed": by_status.get("completed", 0),
        "human_gates_waiting": sum(
            1 for p in proposals
            if p.status == ProposalStatus.ACTIVE and p.current_stage in HUMAN_GATES
        ),
    }
