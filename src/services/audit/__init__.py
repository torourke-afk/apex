"""Audit Service (#14) — Agentic compliance & QA scanning engine.

Provides a registry of compliance rules (FDIC, EHL, Reg DD, UDAAP,
Accessibility, Offer Terms) and a QA scanner (performance heuristics,
link validation, schema.org checks).  Each rule evaluates page content
and returns pass / warn / fail with evidence strings.

Public API
----------
RULES               — master list of ComplianceRule instances
run_compliance_scan  — evaluate all (or filtered) rules against content
run_qa_scan          — Lighthouse-style heuristic scores
run_full_scan        — compliance + QA combined into an AuditReport
get_seed_reports     — three pre-built demo reports
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Callable, Optional

from src.data.seeds._dates import YESTERDAY, NOW

# Shift all hardcoded dates relative to the original anchor date
_ORIG_ANCHOR = date(2026, 7, 16)
_SHIFT = timedelta(days=(YESTERDAY - _ORIG_ANCHOR).days)


def _shift_iso_ts(iso_ts: str) -> str:
    """Shift an ISO timestamp string by _SHIFT days, preserving time and 'Z' suffix."""
    dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00")) + _SHIFT
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    critical = "critical"
    major = "major"
    minor = "minor"


class Verdict(str, Enum):
    passed = "pass"
    warn = "warn"
    fail = "fail"


class RuleCategory(str, Enum):
    FDIC = "FDIC"
    EHL = "EHL"
    RegDD = "RegDD"
    UDAAP = "UDAAP"
    Accessibility = "Accessibility"
    OfferTerms = "OfferTerms"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ComplianceRule:
    """A single compliance check."""

    id: str
    name: str
    category: RuleCategory
    severity: Severity
    check: Callable[[str], ComplianceFinding]
    description: str = ""


@dataclass
class ComplianceFinding:
    rule_id: str
    rule_name: str
    category: str
    severity: str
    verdict: str          # pass | warn | fail
    evidence: str         # human-readable explanation


@dataclass
class QAResult:
    dimension: str        # performance | links | schema | offer_accuracy
    score: float          # 0-100
    details: str


@dataclass
class AuditReport:
    id: str
    target_url: str
    created_at: str
    scan_type: str                       # compliance | qa | full
    compliance_results: list[ComplianceFinding] = field(default_factory=list)
    qa_results: list[QAResult] = field(default_factory=list)
    overall_score: float = 0.0
    pass_count: int = 0
    warn_count: int = 0
    fail_count: int = 0


# ---------------------------------------------------------------------------
# Rule check functions
# ---------------------------------------------------------------------------

def _check_fdic_disclosure(content: str) -> ComplianceFinding:
    """Member FDIC disclosure must appear on the page."""
    patterns = [r"member\s+fdic", r"fdic[\s-]+insured", r"federal\s+deposit\s+insurance"]
    found = any(re.search(p, content, re.IGNORECASE) for p in patterns)
    return ComplianceFinding(
        rule_id="FDIC-001",
        rule_name="Member FDIC Disclosure",
        category=RuleCategory.FDIC.value,
        severity=Severity.critical.value,
        verdict=Verdict.passed.value if found else Verdict.fail.value,
        evidence="'Member FDIC' text found." if found else "Missing 'Member FDIC' disclosure.",
    )


def _check_ehl(content: str) -> ComplianceFinding:
    """Equal Housing Lender logo/text must appear."""
    patterns = [r"equal\s+housing\s+lender", r"ehl", r"equal\s+housing\s+opportunity"]
    found = any(re.search(p, content, re.IGNORECASE) for p in patterns)
    return ComplianceFinding(
        rule_id="EHL-001",
        rule_name="Equal Housing Lender",
        category=RuleCategory.EHL.value,
        severity=Severity.critical.value,
        verdict=Verdict.passed.value if found else Verdict.fail.value,
        evidence="Equal Housing Lender text/logo present." if found else "Missing Equal Housing Lender disclosure.",
    )


def _check_reg_dd_apy(content: str) -> ComplianceFinding:
    """Reg DD: APY/rate terms must be present and accurate."""
    apy_match = re.search(r"\b(\d+\.\d+)\s*%?\s*apy\b", content, re.IGNORECASE)
    rate_match = re.search(r"\binterest\s+rate\b", content, re.IGNORECASE)
    if apy_match and rate_match:
        return ComplianceFinding(
            rule_id="REGDD-001",
            rule_name="Reg DD APY/Rate Terms",
            category=RuleCategory.RegDD.value,
            severity=Severity.critical.value,
            verdict=Verdict.passed.value,
            evidence=f"APY ({apy_match.group(1)}%) and interest rate terms found.",
        )
    if apy_match:
        return ComplianceFinding(
            rule_id="REGDD-001",
            rule_name="Reg DD APY/Rate Terms",
            category=RuleCategory.RegDD.value,
            severity=Severity.critical.value,
            verdict=Verdict.warn.value,
            evidence="APY disclosed but interest rate language missing — verify Reg DD compliance.",
        )
    return ComplianceFinding(
        rule_id="REGDD-001",
        rule_name="Reg DD APY/Rate Terms",
        category=RuleCategory.RegDD.value,
        severity=Severity.critical.value,
        verdict=Verdict.fail.value,
        evidence="No APY or rate disclosures found on page.",
    )


def _check_offer_terms(content: str) -> ComplianceFinding:
    """Offer terms (e.g. '$350 bonus') must have qualifying disclosures."""
    offer_match = re.search(r"\$\d[\d,]*\s*(bonus|cash\s*back|reward|offer)", content, re.IGNORECASE)
    disclosure = re.search(r"(terms?\s+(and|&)\s+conditions?|see\s+details|offer\s+details|restrictions?\s+apply)", content, re.IGNORECASE)
    if not offer_match:
        return ComplianceFinding(
            rule_id="OFFER-001",
            rule_name="Offer T&C Disclosure",
            category=RuleCategory.OfferTerms.value,
            severity=Severity.major.value,
            verdict=Verdict.passed.value,
            evidence="No offer claims detected — rule not applicable.",
        )
    if disclosure:
        return ComplianceFinding(
            rule_id="OFFER-001",
            rule_name="Offer T&C Disclosure",
            category=RuleCategory.OfferTerms.value,
            severity=Severity.major.value,
            verdict=Verdict.passed.value,
            evidence=f"Offer '{offer_match.group(0).strip()}' with qualifying disclosure present.",
        )
    return ComplianceFinding(
        rule_id="OFFER-001",
        rule_name="Offer T&C Disclosure",
        category=RuleCategory.OfferTerms.value,
        severity=Severity.major.value,
        verdict=Verdict.fail.value,
        evidence=f"Offer '{offer_match.group(0).strip()}' found without qualifying terms & conditions.",
    )


def _check_udaap_free(content: str) -> ComplianceFinding:
    """UDAAP: 'free' / 'no fee' claims must have qualification."""
    free_match = re.search(r"\b(free|no[\s-]*fee|zero[\s-]*cost)\b", content, re.IGNORECASE)
    if not free_match:
        return ComplianceFinding(
            rule_id="UDAAP-001",
            rule_name="UDAAP Free/No-Fee Claims",
            category=RuleCategory.UDAAP.value,
            severity=Severity.major.value,
            verdict=Verdict.passed.value,
            evidence="No 'free' or 'no fee' claims detected.",
        )
    qualifier = re.search(
        r"(subject\s+to|conditions?\s+apply|qualifying|with\s+eligible|minimum\s+balance|see\s+details|restrictions?\s+apply)",
        content, re.IGNORECASE,
    )
    if qualifier:
        return ComplianceFinding(
            rule_id="UDAAP-001",
            rule_name="UDAAP Free/No-Fee Claims",
            category=RuleCategory.UDAAP.value,
            severity=Severity.major.value,
            verdict=Verdict.passed.value,
            evidence=f"'{free_match.group(0)}' claim found with qualifying language.",
        )
    return ComplianceFinding(
        rule_id="UDAAP-001",
        rule_name="UDAAP Free/No-Fee Claims",
        category=RuleCategory.UDAAP.value,
        severity=Severity.major.value,
        verdict=Verdict.fail.value,
        evidence=f"'{free_match.group(0)}' claim without qualification — potential UDAAP violation.",
    )


def _check_udaap_comparative(content: str) -> ComplianceFinding:
    """UDAAP: comparative/superlative claims must cite substantiation."""
    superlatives = re.search(
        r"\b(best|lowest|highest|fastest|cheapest|#1|number[\s-]*one|top[\s-]*rated|industry[\s-]*leading|most\s+\w+)\b",
        content, re.IGNORECASE,
    )
    if not superlatives:
        return ComplianceFinding(
            rule_id="UDAAP-002",
            rule_name="UDAAP Comparative Claims",
            category=RuleCategory.UDAAP.value,
            severity=Severity.major.value,
            verdict=Verdict.passed.value,
            evidence="No comparative or superlative claims detected.",
        )
    citation = re.search(
        r"(according\s+to|source:|based\s+on|survey|j\.?d\.?\s*power|bankrate|nerdwallet|\d{4}\s+report)",
        content, re.IGNORECASE,
    )
    if citation:
        return ComplianceFinding(
            rule_id="UDAAP-002",
            rule_name="UDAAP Comparative Claims",
            category=RuleCategory.UDAAP.value,
            severity=Severity.major.value,
            verdict=Verdict.passed.value,
            evidence=f"Comparative claim '{superlatives.group(0)}' found with substantiation.",
        )
    return ComplianceFinding(
        rule_id="UDAAP-002",
        rule_name="UDAAP Comparative Claims",
        category=RuleCategory.UDAAP.value,
        severity=Severity.major.value,
        verdict=Verdict.warn.value,
        evidence=f"Comparative claim '{superlatives.group(0)}' without visible substantiation.",
    )


def _check_a11y_alt_text(content: str) -> ComplianceFinding:
    """Accessibility: all <img> tags should have alt attributes."""
    imgs = re.findall(r"<img\b[^>]*>", content, re.IGNORECASE)
    if not imgs:
        return ComplianceFinding(
            rule_id="A11Y-001",
            rule_name="Image Alt Text",
            category=RuleCategory.Accessibility.value,
            severity=Severity.major.value,
            verdict=Verdict.passed.value,
            evidence="No images found — rule not applicable.",
        )
    missing = [tag for tag in imgs if not re.search(r'\balt\s*=', tag, re.IGNORECASE)]
    if not missing:
        return ComplianceFinding(
            rule_id="A11Y-001",
            rule_name="Image Alt Text",
            category=RuleCategory.Accessibility.value,
            severity=Severity.major.value,
            verdict=Verdict.passed.value,
            evidence=f"All {len(imgs)} image(s) have alt attributes.",
        )
    return ComplianceFinding(
        rule_id="A11Y-001",
        rule_name="Image Alt Text",
        category=RuleCategory.Accessibility.value,
        severity=Severity.major.value,
        verdict=Verdict.fail.value,
        evidence=f"{len(missing)} of {len(imgs)} image(s) missing alt text.",
    )


def _check_a11y_heading_hierarchy(content: str) -> ComplianceFinding:
    """Accessibility: heading levels should not skip (h1->h3 without h2)."""
    headings = re.findall(r"<h(\d)\b", content, re.IGNORECASE)
    levels = [int(h) for h in headings]
    if not levels:
        return ComplianceFinding(
            rule_id="A11Y-002",
            rule_name="Heading Hierarchy",
            category=RuleCategory.Accessibility.value,
            severity=Severity.minor.value,
            verdict=Verdict.warn.value,
            evidence="No headings found on page.",
        )
    skips: list[str] = []
    for i in range(1, len(levels)):
        if levels[i] > levels[i - 1] + 1:
            skips.append(f"h{levels[i-1]}->h{levels[i]}")
    if not skips:
        return ComplianceFinding(
            rule_id="A11Y-002",
            rule_name="Heading Hierarchy",
            category=RuleCategory.Accessibility.value,
            severity=Severity.minor.value,
            verdict=Verdict.passed.value,
            evidence=f"Heading hierarchy valid ({len(levels)} headings, no skips).",
        )
    return ComplianceFinding(
        rule_id="A11Y-002",
        rule_name="Heading Hierarchy",
        category=RuleCategory.Accessibility.value,
        severity=Severity.minor.value,
        verdict=Verdict.fail.value,
        evidence=f"Heading level skips detected: {', '.join(skips)}.",
    )


def _check_a11y_color_contrast(content: str) -> ComplianceFinding:
    """Accessibility: simulated contrast check (flags light-on-light patterns)."""
    low_contrast = re.search(
        r"color\s*:\s*#(fff|fefefe|f[0-9a-f]{5})\b.*background[^;]*:\s*#(fff|fefefe|f[0-9a-f]{5})",
        content, re.IGNORECASE | re.DOTALL,
    )
    if low_contrast:
        return ComplianceFinding(
            rule_id="A11Y-003",
            rule_name="Color Contrast",
            category=RuleCategory.Accessibility.value,
            severity=Severity.major.value,
            verdict=Verdict.warn.value,
            evidence="Potential low-contrast color combination detected in inline styles.",
        )
    return ComplianceFinding(
        rule_id="A11Y-003",
        rule_name="Color Contrast",
        category=RuleCategory.Accessibility.value,
        severity=Severity.major.value,
        verdict=Verdict.passed.value,
        evidence="No obvious low-contrast patterns found (full audit recommended).",
    )


def _check_a11y_form_labels(content: str) -> ComplianceFinding:
    """Accessibility: <input>/<select>/<textarea> should have associated <label> or aria-label."""
    inputs = re.findall(r"<(input|select|textarea)\b[^>]*>", content, re.IGNORECASE)
    if not inputs:
        return ComplianceFinding(
            rule_id="A11Y-004",
            rule_name="Form Labels",
            category=RuleCategory.Accessibility.value,
            severity=Severity.major.value,
            verdict=Verdict.passed.value,
            evidence="No form inputs found — rule not applicable.",
        )
    unlabeled: list[str] = []
    for tag_match in re.finditer(r"<(input|select|textarea)\b[^>]*>", content, re.IGNORECASE):
        tag = tag_match.group(0)
        # Skip hidden inputs
        if re.search(r'type\s*=\s*["\']hidden', tag, re.IGNORECASE):
            continue
        has_aria = re.search(r"aria-label", tag, re.IGNORECASE)
        id_match = re.search(r'id\s*=\s*["\']([^"\']+)', tag, re.IGNORECASE)
        has_for_label = False
        if id_match:
            has_for_label = bool(re.search(
                rf'<label\b[^>]*for\s*=\s*["\']' + re.escape(id_match.group(1)),
                content, re.IGNORECASE,
            ))
        if not has_aria and not has_for_label:
            unlabeled.append(tag_match.group(1))
    if not unlabeled:
        return ComplianceFinding(
            rule_id="A11Y-004",
            rule_name="Form Labels",
            category=RuleCategory.Accessibility.value,
            severity=Severity.major.value,
            verdict=Verdict.passed.value,
            evidence=f"All {len(inputs)} form input(s) have associated labels.",
        )
    return ComplianceFinding(
        rule_id="A11Y-004",
        rule_name="Form Labels",
        category=RuleCategory.Accessibility.value,
        severity=Severity.major.value,
        verdict=Verdict.fail.value,
        evidence=f"{len(unlabeled)} form element(s) missing labels: {', '.join(unlabeled[:5])}.",
    )


def _check_cta_links(content: str) -> ComplianceFinding:
    """CTA links should be present and use valid href (not '#' or 'javascript:')."""
    anchors = re.findall(r"<a\b[^>]*>", content, re.IGNORECASE)
    if not anchors:
        return ComplianceFinding(
            rule_id="CTA-001",
            rule_name="CTA Links Valid",
            category=RuleCategory.OfferTerms.value,
            severity=Severity.minor.value,
            verdict=Verdict.warn.value,
            evidence="No links found on page.",
        )
    broken: list[str] = []
    for tag in anchors:
        href = re.search(r'href\s*=\s*["\']([^"\']*)', tag, re.IGNORECASE)
        if not href:
            broken.append("(no href)")
        elif href.group(1).strip() in ("", "#", "javascript:void(0)", "javascript:;"):
            broken.append(href.group(1) or "(empty)")
    if not broken:
        return ComplianceFinding(
            rule_id="CTA-001",
            rule_name="CTA Links Valid",
            category=RuleCategory.OfferTerms.value,
            severity=Severity.minor.value,
            verdict=Verdict.passed.value,
            evidence=f"All {len(anchors)} link(s) have valid href values.",
        )
    return ComplianceFinding(
        rule_id="CTA-001",
        rule_name="CTA Links Valid",
        category=RuleCategory.OfferTerms.value,
        severity=Severity.minor.value,
        verdict=Verdict.fail.value,
        evidence=f"{len(broken)} link(s) with invalid hrefs: {', '.join(broken[:5])}.",
    )


def _check_schema_jsonld(content: str) -> ComplianceFinding:
    """Schema.org JSON-LD should be present and contain @context/@type."""
    ld_blocks = re.findall(
        r'<script[^>]*type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        content, re.IGNORECASE | re.DOTALL,
    )
    if not ld_blocks:
        return ComplianceFinding(
            rule_id="SCHEMA-001",
            rule_name="Schema.org JSON-LD",
            category=RuleCategory.OfferTerms.value,
            severity=Severity.minor.value,
            verdict=Verdict.fail.value,
            evidence="No JSON-LD structured data found on page.",
        )
    valid = 0
    for block in ld_blocks:
        if "@context" in block and "@type" in block:
            valid += 1
    if valid == len(ld_blocks):
        return ComplianceFinding(
            rule_id="SCHEMA-001",
            rule_name="Schema.org JSON-LD",
            category=RuleCategory.OfferTerms.value,
            severity=Severity.minor.value,
            verdict=Verdict.passed.value,
            evidence=f"{valid} valid JSON-LD block(s) found with @context and @type.",
        )
    return ComplianceFinding(
        rule_id="SCHEMA-001",
        rule_name="Schema.org JSON-LD",
        category=RuleCategory.OfferTerms.value,
        severity=Severity.minor.value,
        verdict=Verdict.warn.value,
        evidence=f"{valid} of {len(ld_blocks)} JSON-LD block(s) valid — some missing @context/@type.",
    )


# ---------------------------------------------------------------------------
# Rule registry
# ---------------------------------------------------------------------------

RULES: list[ComplianceRule] = [
    ComplianceRule(
        id="FDIC-001", name="Member FDIC Disclosure", category=RuleCategory.FDIC,
        severity=Severity.critical, check=_check_fdic_disclosure,
        description="Verify 'Member FDIC' disclosure is present on the page.",
    ),
    ComplianceRule(
        id="EHL-001", name="Equal Housing Lender", category=RuleCategory.EHL,
        severity=Severity.critical, check=_check_ehl,
        description="Verify Equal Housing Lender logo or text is present.",
    ),
    ComplianceRule(
        id="REGDD-001", name="Reg DD APY/Rate Terms", category=RuleCategory.RegDD,
        severity=Severity.critical, check=_check_reg_dd_apy,
        description="Verify APY and interest rate disclosures per Regulation DD.",
    ),
    ComplianceRule(
        id="OFFER-001", name="Offer T&C Disclosure", category=RuleCategory.OfferTerms,
        severity=Severity.major, check=_check_offer_terms,
        description="Offer claims (e.g. '$350 bonus') must have qualifying T&C disclosure.",
    ),
    ComplianceRule(
        id="UDAAP-001", name="UDAAP Free/No-Fee Claims", category=RuleCategory.UDAAP,
        severity=Severity.major, check=_check_udaap_free,
        description="'Free' or 'no fee' claims must include qualifying language.",
    ),
    ComplianceRule(
        id="UDAAP-002", name="UDAAP Comparative Claims", category=RuleCategory.UDAAP,
        severity=Severity.major, check=_check_udaap_comparative,
        description="Superlative/comparative claims must cite substantiation.",
    ),
    ComplianceRule(
        id="A11Y-001", name="Image Alt Text", category=RuleCategory.Accessibility,
        severity=Severity.major, check=_check_a11y_alt_text,
        description="All images must have alt text for screen readers.",
    ),
    ComplianceRule(
        id="A11Y-002", name="Heading Hierarchy", category=RuleCategory.Accessibility,
        severity=Severity.minor, check=_check_a11y_heading_hierarchy,
        description="Heading levels (h1-h6) must not skip levels.",
    ),
    ComplianceRule(
        id="A11Y-003", name="Color Contrast", category=RuleCategory.Accessibility,
        severity=Severity.major, check=_check_a11y_color_contrast,
        description="Text/background combinations must meet WCAG AA contrast ratios.",
    ),
    ComplianceRule(
        id="A11Y-004", name="Form Labels", category=RuleCategory.Accessibility,
        severity=Severity.major, check=_check_a11y_form_labels,
        description="Form inputs must have associated labels or aria-label.",
    ),
    ComplianceRule(
        id="CTA-001", name="CTA Links Valid", category=RuleCategory.OfferTerms,
        severity=Severity.minor, check=_check_cta_links,
        description="CTA links must have valid, non-placeholder hrefs.",
    ),
    ComplianceRule(
        id="SCHEMA-001", name="Schema.org JSON-LD", category=RuleCategory.OfferTerms,
        severity=Severity.minor, check=_check_schema_jsonld,
        description="Page must contain valid Schema.org JSON-LD structured data.",
    ),
]


# ---------------------------------------------------------------------------
# Scan runners
# ---------------------------------------------------------------------------

def run_compliance_scan(content: str, categories: Optional[list[str]] = None) -> list[ComplianceFinding]:
    """Run all compliance rules against *content*, optionally filtered by categories."""
    findings: list[ComplianceFinding] = []
    for rule in RULES:
        if categories and rule.category.value not in categories:
            continue
        findings.append(rule.check(content))
    return findings


def _score_performance(content: str) -> QAResult:
    """Heuristic performance score based on page weight and complexity."""
    length = len(content)
    img_count = len(re.findall(r"<img\b", content, re.IGNORECASE))
    script_count = len(re.findall(r"<script\b", content, re.IGNORECASE))
    # Simple heuristic: deduct for size and resource counts
    score = 100.0
    if length > 500_000:
        score -= 30
    elif length > 200_000:
        score -= 15
    elif length > 100_000:
        score -= 5
    score -= min(img_count * 2, 20)
    score -= min(script_count * 3, 20)
    score = max(score, 0)
    return QAResult(
        dimension="performance",
        score=round(score, 1),
        details=f"Page size: {length:,} chars, {img_count} images, {script_count} scripts.",
    )


def _score_links(content: str) -> QAResult:
    """Crawl links in the content for placeholder/broken patterns."""
    anchors = re.findall(r'href\s*=\s*["\']([^"\']*)', content, re.IGNORECASE)
    total = len(anchors)
    if total == 0:
        return QAResult(dimension="links", score=50.0, details="No links found on page.")
    broken = sum(
        1 for h in anchors
        if h.strip() in ("", "#", "javascript:void(0)", "javascript:;")
    )
    score = round((1 - broken / total) * 100, 1) if total else 100.0
    return QAResult(
        dimension="links",
        score=score,
        details=f"{total} links, {broken} broken/placeholder.",
    )


def _score_schema(content: str) -> QAResult:
    """Score JSON-LD presence and validity."""
    ld_blocks = re.findall(
        r'<script[^>]*type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        content, re.IGNORECASE | re.DOTALL,
    )
    if not ld_blocks:
        return QAResult(dimension="schema", score=0.0, details="No JSON-LD structured data found.")
    valid = sum(1 for b in ld_blocks if "@context" in b and "@type" in b)
    score = round(valid / len(ld_blocks) * 100, 1)
    return QAResult(
        dimension="schema",
        score=score,
        details=f"{valid}/{len(ld_blocks)} JSON-LD blocks valid.",
    )


def _score_offer_accuracy(content: str) -> QAResult:
    """Reconcile offer amounts with disclosure language."""
    offers = re.findall(r"\$(\d[\d,]*)\s*(bonus|cash\s*back|reward|offer)", content, re.IGNORECASE)
    if not offers:
        return QAResult(dimension="offer_accuracy", score=100.0, details="No offer claims to reconcile.")
    disclosures = len(re.findall(
        r"(terms?\s+(and|&)\s+conditions?|see\s+details|offer\s+details|restrictions?\s+apply)",
        content, re.IGNORECASE,
    ))
    ratio = min(disclosures / len(offers), 1.0)
    score = round(ratio * 100, 1)
    return QAResult(
        dimension="offer_accuracy",
        score=score,
        details=f"{len(offers)} offer claim(s), {disclosures} qualifying disclosure(s).",
    )


def run_qa_scan(content: str) -> list[QAResult]:
    """Run QA heuristic checks against content."""
    return [
        _score_performance(content),
        _score_links(content),
        _score_schema(content),
        _score_offer_accuracy(content),
    ]


def _compute_overall(
    compliance: list[ComplianceFinding],
    qa: list[QAResult],
) -> tuple[float, int, int, int]:
    """Compute overall score and pass/warn/fail counts."""
    pass_count = sum(1 for f in compliance if f.verdict == Verdict.passed.value)
    warn_count = sum(1 for f in compliance if f.verdict == Verdict.warn.value)
    fail_count = sum(1 for f in compliance if f.verdict == Verdict.fail.value)
    total = len(compliance)
    compliance_score = (pass_count / total * 100) if total else 100.0
    qa_avg = (sum(q.score for q in qa) / len(qa)) if qa else 100.0
    overall = round(compliance_score * 0.6 + qa_avg * 0.4, 1)
    return overall, pass_count, warn_count, fail_count


def run_full_scan(target_url: str, content: str) -> AuditReport:
    """Run a combined compliance + QA scan and return an AuditReport."""
    compliance = run_compliance_scan(content)
    qa = run_qa_scan(content)
    overall, pc, wc, fc = _compute_overall(compliance, qa)
    return AuditReport(
        id=str(uuid.uuid4()),
        target_url=target_url,
        created_at=datetime.now(timezone.utc).isoformat(),
        scan_type="full",
        compliance_results=compliance,
        qa_results=qa,
        overall_score=overall,
        pass_count=pc,
        warn_count=wc,
        fail_count=fc,
    )


# ---------------------------------------------------------------------------
# Seed data — three pre-built demo reports
# ---------------------------------------------------------------------------

def get_seed_reports() -> list[AuditReport]:
    """Return three sample audit reports with mixed pass/warn/fail findings."""
    return [
        AuditReport(
            id="aud-seed-001",
            target_url="https://www.fifththird.com/checking",
            created_at=_shift_iso_ts("2026-07-10T14:22:00Z"),
            scan_type="full",
            compliance_results=[
                ComplianceFinding("FDIC-001", "Member FDIC Disclosure", "FDIC", "critical", "pass", "'Member FDIC' text found in footer."),
                ComplianceFinding("EHL-001", "Equal Housing Lender", "EHL", "critical", "pass", "Equal Housing Lender logo present in footer."),
                ComplianceFinding("REGDD-001", "Reg DD APY/Rate Terms", "RegDD", "critical", "pass", "APY (0.01%) and interest rate terms found."),
                ComplianceFinding("OFFER-001", "Offer T&C Disclosure", "OfferTerms", "major", "pass", "Offer '$250 bonus' with qualifying disclosure present."),
                ComplianceFinding("UDAAP-001", "UDAAP Free/No-Fee Claims", "UDAAP", "major", "pass", "'Free' claim found with qualifying language."),
                ComplianceFinding("UDAAP-002", "UDAAP Comparative Claims", "UDAAP", "major", "pass", "No comparative or superlative claims detected."),
                ComplianceFinding("A11Y-001", "Image Alt Text", "Accessibility", "major", "pass", "All 8 image(s) have alt attributes."),
                ComplianceFinding("A11Y-002", "Heading Hierarchy", "Accessibility", "minor", "pass", "Heading hierarchy valid (6 headings, no skips)."),
                ComplianceFinding("A11Y-003", "Color Contrast", "Accessibility", "major", "pass", "No obvious low-contrast patterns found."),
                ComplianceFinding("A11Y-004", "Form Labels", "Accessibility", "major", "fail", "2 form element(s) missing labels: input, select."),
                ComplianceFinding("CTA-001", "CTA Links Valid", "OfferTerms", "minor", "pass", "All 14 link(s) have valid href values."),
                ComplianceFinding("SCHEMA-001", "Schema.org JSON-LD", "OfferTerms", "minor", "pass", "2 valid JSON-LD block(s) found."),
            ],
            qa_results=[
                QAResult("performance", 82.0, "Page size: 145,000 chars, 8 images, 6 scripts."),
                QAResult("links", 100.0, "14 links, 0 broken/placeholder."),
                QAResult("schema", 100.0, "2/2 JSON-LD blocks valid."),
                QAResult("offer_accuracy", 100.0, "1 offer claim(s), 1 qualifying disclosure(s)."),
            ],
            overall_score=88.2,
            pass_count=11,
            warn_count=0,
            fail_count=1,
        ),
        AuditReport(
            id="aud-seed-002",
            target_url="https://www.fifththird.com/savings/high-yield",
            created_at=_shift_iso_ts("2026-07-12T09:15:00Z"),
            scan_type="compliance",
            compliance_results=[
                ComplianceFinding("FDIC-001", "Member FDIC Disclosure", "FDIC", "critical", "pass", "'Member FDIC' text found in footer."),
                ComplianceFinding("EHL-001", "Equal Housing Lender", "EHL", "critical", "fail", "Missing Equal Housing Lender disclosure."),
                ComplianceFinding("REGDD-001", "Reg DD APY/Rate Terms", "RegDD", "critical", "warn", "APY disclosed but interest rate language missing."),
                ComplianceFinding("OFFER-001", "Offer T&C Disclosure", "OfferTerms", "major", "fail", "Offer '$350 bonus' found without qualifying terms & conditions."),
                ComplianceFinding("UDAAP-001", "UDAAP Free/No-Fee Claims", "UDAAP", "major", "fail", "'No-fee' claim without qualification — potential UDAAP violation."),
                ComplianceFinding("UDAAP-002", "UDAAP Comparative Claims", "UDAAP", "major", "warn", "Comparative claim 'best' without visible substantiation."),
                ComplianceFinding("A11Y-001", "Image Alt Text", "Accessibility", "major", "fail", "3 of 5 image(s) missing alt text."),
                ComplianceFinding("A11Y-002", "Heading Hierarchy", "Accessibility", "minor", "fail", "Heading level skips detected: h1->h3."),
                ComplianceFinding("A11Y-003", "Color Contrast", "Accessibility", "major", "warn", "Potential low-contrast color combination detected."),
                ComplianceFinding("A11Y-004", "Form Labels", "Accessibility", "major", "pass", "All 2 form input(s) have associated labels."),
                ComplianceFinding("CTA-001", "CTA Links Valid", "OfferTerms", "minor", "fail", "2 link(s) with invalid hrefs: #, javascript:void(0)."),
                ComplianceFinding("SCHEMA-001", "Schema.org JSON-LD", "OfferTerms", "minor", "fail", "No JSON-LD structured data found on page."),
            ],
            qa_results=[],
            overall_score=25.0,
            pass_count=3,
            warn_count=3,
            fail_count=6,
        ),
        AuditReport(
            id="aud-seed-003",
            target_url="https://www.fifththird.com/mortgage/apply",
            created_at=_shift_iso_ts("2026-07-15T16:45:00Z"),
            scan_type="qa",
            compliance_results=[],
            qa_results=[
                QAResult("performance", 65.0, "Page size: 280,000 chars, 12 images, 9 scripts."),
                QAResult("links", 85.7, "21 links, 3 broken/placeholder."),
                QAResult("schema", 50.0, "1/2 JSON-LD blocks valid."),
                QAResult("offer_accuracy", 50.0, "2 offer claim(s), 1 qualifying disclosure(s)."),
            ],
            overall_score=62.7,
            pass_count=0,
            warn_count=0,
            fail_count=0,
        ),
    ]
