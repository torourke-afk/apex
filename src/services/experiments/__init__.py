"""Experiments Service (#15) — A/B testing engine with statistical analysis.

Provides:
- Experiment lifecycle management (draft → running → paused → completed → archived)
- Two-proportion z-test for significance testing
- Power analysis for sample-size estimation
- O'Brien-Fleming sequential testing boundaries
- Lift calculation with confidence intervals
- Seed data: 5 experiments at various stages
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Try scipy for accuracy; fall back to pure-Python approximations
# ---------------------------------------------------------------------------
try:
    from scipy.stats import norm as _norm

    def _norm_cdf(x: float) -> float:
        return float(_norm.cdf(x))

    def _norm_ppf(p: float) -> float:
        return float(_norm.ppf(p))

except ImportError:
    # Pure-Python standard-normal CDF (Abramowitz & Stegun approximation)
    def _norm_cdf(x: float) -> float:
        """Cumulative distribution function for the standard normal."""
        a1, a2, a3, a4, a5 = (
            0.254829592,
            -0.284496736,
            1.421413741,
            -1.453152027,
            1.061405429,
        )
        p = 0.3275911
        sign = 1.0 if x >= 0 else -1.0
        x_abs = abs(x) / math.sqrt(2.0)
        t = 1.0 / (1.0 + p * x_abs)
        y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(
            -x_abs * x_abs
        )
        return 0.5 * (1.0 + sign * y)

    # Pure-Python inverse normal (rational approximation, Beasley-Springer-Moro)
    def _norm_ppf(p: float) -> float:
        """Inverse CDF (percent-point function) for the standard normal."""
        if p <= 0.0:
            return -math.inf
        if p >= 1.0:
            return math.inf
        if p == 0.5:
            return 0.0

        # Rational approximation coefficients
        a = [
            -3.969683028665376e01,
            2.209460984245205e02,
            -2.759285104469687e02,
            1.383577518672690e02,
            -3.066479806614716e01,
            2.506628277459239e00,
        ]
        b = [
            -5.447609879822406e01,
            1.615858368580409e02,
            -1.556989798598866e02,
            6.680131188771972e01,
            -1.328068155288572e01,
        ]
        c = [
            -7.784894002430293e-03,
            -3.223964580411365e-01,
            -2.400758277161838e00,
            -2.549732539343734e00,
            4.374664141464968e00,
            2.938163982698783e00,
        ]
        d = [
            7.784695709041462e-03,
            3.224671290700398e-01,
            2.445134137142996e00,
            3.754408661907416e00,
        ]

        p_low = 0.02425
        p_high = 1.0 - p_low

        if p < p_low:
            q = math.sqrt(-2.0 * math.log(p))
            return (
                ((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]
            ) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
        elif p <= p_high:
            q = p - 0.5
            r = q * q
            return (
                (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
                * q
            ) / (
                ((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0
            )
        else:
            q = math.sqrt(-2.0 * math.log(1.0 - p))
            return -(
                ((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]
            ) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------

class ExperimentStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


@dataclass
class Variant:
    name: str
    traffic_pct: float  # 0..1
    visitors: int = 0
    conversions: int = 0

    @property
    def conversion_rate(self) -> float:
        return self.conversions / self.visitors if self.visitors > 0 else 0.0


@dataclass
class ExperimentResults:
    winner: str | None = None
    lift: float | None = None
    lift_ci_lower: float | None = None
    lift_ci_upper: float | None = None
    z_stat: float | None = None
    p_value: float | None = None
    confidence_level: float | None = None
    is_significant: bool = False
    power: float | None = None
    underpowered: bool = False


@dataclass
class Experiment:
    id: str
    name: str
    hypothesis: str
    metric: str  # primary KPI
    status: ExperimentStatus
    variants: list[Variant] = field(default_factory=list)
    start_date: str | None = None  # ISO date
    end_date: str | None = None
    planned_sample: int = 0
    results: ExperimentResults | None = None


# ---------------------------------------------------------------------------
# Statistical engine
# ---------------------------------------------------------------------------

def two_proportion_z_test(
    visitors_a: int,
    conversions_a: int,
    visitors_b: int,
    conversions_b: int,
    alpha: float = 0.05,
) -> dict[str, Any]:
    """Two-proportion z-test for A/B conversion comparison.

    Returns z-statistic, p-value (two-sided), and confidence interval for
    the difference in proportions (p_b - p_a).
    """
    if visitors_a <= 0 or visitors_b <= 0:
        return {
            "z_stat": 0.0,
            "p_value": 1.0,
            "ci_lower": 0.0,
            "ci_upper": 0.0,
            "rate_a": 0.0,
            "rate_b": 0.0,
            "diff": 0.0,
            "is_significant": False,
        }

    p_a = conversions_a / visitors_a
    p_b = conversions_b / visitors_b
    diff = p_b - p_a

    # Pooled proportion under H0
    p_pool = (conversions_a + conversions_b) / (visitors_a + visitors_b)
    se_pool = math.sqrt(p_pool * (1.0 - p_pool) * (1.0 / visitors_a + 1.0 / visitors_b))

    if se_pool < 1e-12:
        return {
            "z_stat": 0.0,
            "p_value": 1.0,
            "ci_lower": 0.0,
            "ci_upper": 0.0,
            "rate_a": p_a,
            "rate_b": p_b,
            "diff": diff,
            "is_significant": False,
        }

    z_stat = diff / se_pool
    p_value = 2.0 * (1.0 - _norm_cdf(abs(z_stat)))

    # CI for the difference using unpooled SE
    se_diff = math.sqrt(
        p_a * (1.0 - p_a) / visitors_a + p_b * (1.0 - p_b) / visitors_b
    )
    z_crit = _norm_ppf(1.0 - alpha / 2.0)
    ci_lower = diff - z_crit * se_diff
    ci_upper = diff + z_crit * se_diff

    return {
        "z_stat": round(z_stat, 4),
        "p_value": round(p_value, 6),
        "ci_lower": round(ci_lower, 6),
        "ci_upper": round(ci_upper, 6),
        "rate_a": round(p_a, 6),
        "rate_b": round(p_b, 6),
        "diff": round(diff, 6),
        "is_significant": p_value < alpha,
    }


def power_analysis(
    baseline_rate: float,
    minimum_detectable_effect: float,
    alpha: float = 0.05,
    power: float = 0.80,
) -> dict[str, Any]:
    """Compute required sample size per variant for a two-proportion test.

    Uses the normal approximation formula:
        n = (z_alpha/2 + z_beta)^2 * (p1*(1-p1) + p2*(1-p2)) / (p2 - p1)^2
    """
    p1 = baseline_rate
    p2 = baseline_rate + minimum_detectable_effect

    if abs(p2 - p1) < 1e-12:
        return {
            "sample_size_per_variant": math.inf,
            "total_sample_size": math.inf,
            "baseline_rate": baseline_rate,
            "mde": minimum_detectable_effect,
            "alpha": alpha,
            "power": power,
        }

    z_alpha = _norm_ppf(1.0 - alpha / 2.0)
    z_beta = _norm_ppf(power)

    numerator = (z_alpha + z_beta) ** 2 * (p1 * (1.0 - p1) + p2 * (1.0 - p2))
    denominator = (p2 - p1) ** 2

    n = math.ceil(numerator / denominator)

    return {
        "sample_size_per_variant": n,
        "total_sample_size": n * 2,
        "baseline_rate": baseline_rate,
        "mde": minimum_detectable_effect,
        "alpha": alpha,
        "power": power,
    }


def obrien_fleming_boundaries(
    planned_sample: int,
    alpha: float = 0.05,
    n_analyses: int = 4,
) -> list[dict[str, Any]]:
    """Compute O'Brien-Fleming sequential testing boundaries.

    Returns boundary values at each interim analysis (25%, 50%, 75%, 100%
    of the planned sample). The O'Brien-Fleming approach uses:
        z_boundary(t) = z_alpha / sqrt(t)
    where t is the information fraction (0..1).
    """
    z_alpha = _norm_ppf(1.0 - alpha / 2.0)
    fractions = [(i + 1) / n_analyses for i in range(n_analyses)]

    boundaries: list[dict[str, Any]] = []
    for frac in fractions:
        z_boundary = z_alpha / math.sqrt(frac)
        sample_at_look = int(planned_sample * frac)
        p_value_boundary = 2.0 * (1.0 - _norm_cdf(z_boundary))

        boundaries.append({
            "analysis_number": len(boundaries) + 1,
            "information_fraction": round(frac, 4),
            "sample_size": sample_at_look,
            "z_boundary": round(z_boundary, 4),
            "p_value_boundary": round(p_value_boundary, 6),
            "label": f"{int(frac * 100)}% interim",
        })

    return boundaries


def compute_lift(
    rate_a: float,
    rate_b: float,
    visitors_a: int,
    visitors_b: int,
    alpha: float = 0.05,
) -> dict[str, Any]:
    """Compute relative lift (rate_b - rate_a) / rate_a with CI."""
    if rate_a <= 0 or visitors_a <= 0 or visitors_b <= 0:
        return {
            "lift": 0.0,
            "lift_ci_lower": 0.0,
            "lift_ci_upper": 0.0,
        }

    lift = (rate_b - rate_a) / rate_a

    # Delta-method SE for the relative risk: SE(diff) / rate_a
    se_diff = math.sqrt(
        rate_a * (1.0 - rate_a) / visitors_a + rate_b * (1.0 - rate_b) / visitors_b
    )
    se_lift = se_diff / rate_a
    z_crit = _norm_ppf(1.0 - alpha / 2.0)

    return {
        "lift": round(lift, 6),
        "lift_ci_lower": round(lift - z_crit * se_lift, 6),
        "lift_ci_upper": round(lift + z_crit * se_lift, 6),
    }


def compute_achieved_power(
    rate_a: float,
    rate_b: float,
    visitors_a: int,
    visitors_b: int,
    alpha: float = 0.05,
) -> float:
    """Compute achieved (post-hoc) power given observed rates and sample sizes."""
    if visitors_a <= 0 or visitors_b <= 0:
        return 0.0

    diff = abs(rate_b - rate_a)
    if diff < 1e-12:
        return 0.0

    se = math.sqrt(
        rate_a * (1.0 - rate_a) / visitors_a + rate_b * (1.0 - rate_b) / visitors_b
    )
    if se < 1e-12:
        return 1.0

    z_alpha = _norm_ppf(1.0 - alpha / 2.0)
    z_power = diff / se - z_alpha
    return round(_norm_cdf(z_power), 4)


# ---------------------------------------------------------------------------
# Results computation
# ---------------------------------------------------------------------------

def compute_results(experiment: Experiment, alpha: float = 0.05) -> ExperimentResults:
    """Given an experiment with variant data, compute full results."""
    if len(experiment.variants) < 2:
        return ExperimentResults()

    control = experiment.variants[0]
    treatment = experiment.variants[1]

    z_result = two_proportion_z_test(
        control.visitors,
        control.conversions,
        treatment.visitors,
        treatment.conversions,
        alpha=alpha,
    )

    lift_result = compute_lift(
        z_result["rate_a"],
        z_result["rate_b"],
        control.visitors,
        treatment.visitors,
        alpha=alpha,
    )

    achieved_power = compute_achieved_power(
        z_result["rate_a"],
        z_result["rate_b"],
        control.visitors,
        treatment.visitors,
        alpha=alpha,
    )

    # Determine winner
    winner: str | None = None
    if z_result["is_significant"]:
        winner = treatment.name if z_result["diff"] > 0 else control.name

    return ExperimentResults(
        winner=winner,
        lift=lift_result["lift"],
        lift_ci_lower=lift_result["lift_ci_lower"],
        lift_ci_upper=lift_result["lift_ci_upper"],
        z_stat=z_result["z_stat"],
        p_value=z_result["p_value"],
        confidence_level=round(1.0 - z_result["p_value"], 4) if z_result["p_value"] < 1.0 else 0.0,
        is_significant=z_result["is_significant"],
        power=achieved_power,
        underpowered=achieved_power < 0.80,
    )


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

_today = date.today()

SEED_EXPERIMENTS: list[Experiment] = [
    # 1 — Running: checkout CTA test
    Experiment(
        id="exp-001",
        name="Checkout CTA Color Test",
        hypothesis="A green CTA button will increase checkout conversion vs. blue",
        metric="checkout_conversion_rate",
        status=ExperimentStatus.RUNNING,
        variants=[
            Variant(name="Control (Blue)", traffic_pct=0.50, visitors=12_840, conversions=642),
            Variant(name="Variant A (Green)", traffic_pct=0.50, visitors=12_756, conversions=701),
        ],
        start_date=(_today - timedelta(days=14)).isoformat(),
        end_date=(_today + timedelta(days=14)).isoformat(),
        planned_sample=50_000,
    ),
    # 2 — Running: hero banner headline
    Experiment(
        id="exp-002",
        name="Hero Banner Headline Test",
        hypothesis="Benefit-oriented headline will improve landing page CTR vs. feature-oriented",
        metric="hero_ctr",
        status=ExperimentStatus.RUNNING,
        variants=[
            Variant(name="Control (Features)", traffic_pct=0.50, visitors=8_420, conversions=589),
            Variant(name="Variant A (Benefits)", traffic_pct=0.50, visitors=8_380, conversions=653),
        ],
        start_date=(_today - timedelta(days=7)).isoformat(),
        end_date=(_today + timedelta(days=21)).isoformat(),
        planned_sample=40_000,
    ),
    # 3 — Completed with clear winner
    Experiment(
        id="exp-003",
        name="Email Subject Line Personalization",
        hypothesis="Personalized subject lines with first name will increase open rate",
        metric="email_open_rate",
        status=ExperimentStatus.COMPLETED,
        variants=[
            Variant(name="Control (Generic)", traffic_pct=0.50, visitors=25_000, conversions=5_250),
            Variant(name="Variant A (Personalized)", traffic_pct=0.50, visitors=25_000, conversions=6_000),
        ],
        start_date=(_today - timedelta(days=45)).isoformat(),
        end_date=(_today - timedelta(days=15)).isoformat(),
        planned_sample=50_000,
    ),
    # 4 — Completed but underpowered (small sample, ambiguous result)
    Experiment(
        id="exp-004",
        name="Pricing Page Layout Redesign",
        hypothesis="Simplified pricing table will increase plan selection rate",
        metric="plan_selection_rate",
        status=ExperimentStatus.COMPLETED,
        variants=[
            Variant(name="Control (Complex)", traffic_pct=0.50, visitors=1_200, conversions=96),
            Variant(name="Variant A (Simple)", traffic_pct=0.50, visitors=1_180, conversions=106),
        ],
        start_date=(_today - timedelta(days=60)).isoformat(),
        end_date=(_today - timedelta(days=30)).isoformat(),
        planned_sample=20_000,
    ),
    # 5 — Draft: not yet started
    Experiment(
        id="exp-005",
        name="Mobile Nav Hamburger vs. Tab Bar",
        hypothesis="Bottom tab bar navigation will reduce bounce rate on mobile",
        metric="mobile_bounce_rate",
        status=ExperimentStatus.DRAFT,
        variants=[
            Variant(name="Control (Hamburger)", traffic_pct=0.50, visitors=0, conversions=0),
            Variant(name="Variant A (Tab Bar)", traffic_pct=0.50, visitors=0, conversions=0),
        ],
        start_date=None,
        end_date=None,
        planned_sample=30_000,
    ),
]

# Pre-compute results for completed and running experiments
for _exp in SEED_EXPERIMENTS:
    if _exp.status in (ExperimentStatus.RUNNING, ExperimentStatus.COMPLETED):
        _exp.results = compute_results(_exp)


# ---------------------------------------------------------------------------
# In-memory store (for the BFF)
# ---------------------------------------------------------------------------

_store: dict[str, Experiment] = {exp.id: exp for exp in SEED_EXPERIMENTS}


def list_experiments() -> list[Experiment]:
    """Return all experiments."""
    return list(_store.values())


def get_experiment(experiment_id: str) -> Experiment | None:
    """Return a single experiment by ID."""
    return _store.get(experiment_id)


def create_experiment(
    name: str,
    hypothesis: str,
    metric: str,
    variants: list[dict[str, Any]],
) -> Experiment:
    """Create a new experiment in draft status."""
    exp_id = f"exp-{uuid.uuid4().hex[:6]}"
    parsed_variants = [
        Variant(
            name=v["name"],
            traffic_pct=v.get("traffic_pct", 1.0 / max(len(variants), 1)),
            visitors=v.get("visitors", 0),
            conversions=v.get("conversions", 0),
        )
        for v in variants
    ]
    exp = Experiment(
        id=exp_id,
        name=name,
        hypothesis=hypothesis,
        metric=metric,
        status=ExperimentStatus.DRAFT,
        variants=parsed_variants,
    )
    _store[exp_id] = exp
    return exp


def analyze_experiment(experiment_id: str, alpha: float = 0.05) -> Experiment | None:
    """Run statistical analysis on an experiment and persist results."""
    exp = _store.get(experiment_id)
    if exp is None:
        return None
    exp.results = compute_results(exp, alpha=alpha)
    return exp


def get_summary() -> dict[str, Any]:
    """Aggregate stats across all experiments."""
    experiments = list(_store.values())
    total = len(experiments)
    running = sum(1 for e in experiments if e.status == ExperimentStatus.RUNNING)
    completed = sum(1 for e in experiments if e.status == ExperimentStatus.COMPLETED)
    drafts = sum(1 for e in experiments if e.status == ExperimentStatus.DRAFT)

    winners = [
        e for e in experiments
        if e.status == ExperimentStatus.COMPLETED
        and e.results and e.results.winner is not None
    ]
    win_rate = len(winners) / completed if completed > 0 else 0.0

    lifts = [e.results.lift for e in winners if e.results and e.results.lift is not None]
    avg_lift = sum(lifts) / len(lifts) if lifts else 0.0

    return {
        "total": total,
        "running": running,
        "completed": completed,
        "drafts": drafts,
        "win_rate": round(win_rate, 4),
        "avg_lift": round(avg_lift, 4),
    }
