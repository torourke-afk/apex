"""Allocation / Optimization Service (#11) — Next-Best-Dollar marginal allocator.

Core engine for the fitted-response-curve allocator described in
``design/reference/RV-Reference-Capabilities.md``.  Works over
campaign x geo combos, fits log-response curves, solves for the
profit- or volume-optimal allocation within bounded reallocation
bands, and projects a 30-day rollout respecting a <=20%/week
spend-change constraint.

All heavy lifting uses numpy.  Seed data (10 campaigns x 6 DMAs = 60
combos) is deterministic (seed=42) so endpoints work immediately with
no database.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_RNG_SEED = 42

# Reallocation bounds — each combo clamped to [LO_MULT, HI_MULT] of current
# spend.  These match 30 days @ <=20%/week: 0.8^4 ~ 0.41, 1.2^4 ~ 2.07
LO_MULT = 0.4
HI_MULT = 2.0

# Rollout constraint — max weekly spend change fraction
MAX_WEEKLY_CHANGE = 0.20

# Rollout length
ROLLOUT_DAYS = 30
ROLLOUT_WEEKS = 4


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------

class Objective(str, Enum):
    """Optimization objective."""

    PROFIT = "profit"
    VOLUME = "volume"


class Role(str, Enum):
    """Campaign role segment."""

    SCALE = "Scale"
    DEFEND = "Defend"
    MAINTAIN = "Maintain"
    EXPERIMENT = "Experiment"


@dataclass
class Combo:
    """A single campaign x DMA combination with its response curve."""

    campaign: str
    dma: str
    role: Role
    current_spend: float
    # Response curve: accounts = k * ln(1 + spend / s_ref)
    k: float
    s_ref: float
    # Derived at current spend
    current_accounts: float = 0.0
    # Value per account (for profit objective)
    account_value: float = 350.0

    def __post_init__(self) -> None:
        self.current_accounts = self.response(self.current_spend)

    # -- curve evaluation --------------------------------------------------

    def response(self, spend: float) -> float:
        """Evaluate response curve: accounts = k * ln(1 + spend / s_ref)."""
        if spend <= 0:
            return 0.0
        return self.k * math.log(1.0 + spend / self.s_ref)

    def marginal_response(self, spend: float) -> float:
        """First derivative: d(accounts)/d(spend) = k / (s_ref + spend)."""
        return self.k / (self.s_ref + spend)

    def marginal_profit(self, spend: float) -> float:
        """d(profit)/d(spend) = account_value * d(accounts)/d(spend) - 1."""
        return self.account_value * self.marginal_response(spend) - 1.0

    def profit(self, spend: float) -> float:
        """Contribution margin = accounts * value - spend."""
        return self.response(spend) * self.account_value - spend

    # -- bounds ------------------------------------------------------------

    @property
    def spend_lo(self) -> float:
        """Lower bound on spend after reallocation."""
        return self.current_spend * LO_MULT

    @property
    def spend_hi(self) -> float:
        """Upper bound on spend after reallocation."""
        return self.current_spend * HI_MULT


@dataclass
class OptimalAllocation:
    """Result of running the optimizer on one combo."""

    campaign: str
    dma: str
    role: str
    current_spend: float
    optimal_spend: float
    current_accounts: float
    optimal_accounts: float
    current_profit: float
    optimal_profit: float
    waste_gap_accounts: float
    waste_gap_dollars: float
    delta_spend: float
    delta_pct: float


@dataclass
class MoveRecommendation:
    """A single reallocation move."""

    from_campaign: str
    from_dma: str
    to_campaign: str
    to_dma: str
    delta: float
    rationale: str
    roas_impact: float


@dataclass
class RolloutDay:
    """A single day's snapshot in the rollout simulation."""

    day: int
    total_spend: float
    total_accounts: float
    total_profit: float
    pct_progress: float


@dataclass
class OptimizationResult:
    """Full result from running the allocator."""

    objective: str
    budget: float
    allocations: list[OptimalAllocation]
    top_moves: list[MoveRecommendation]
    total_current_spend: float
    total_optimal_spend: float
    total_current_accounts: float
    total_optimal_accounts: float
    total_current_profit: float
    total_optimal_profit: float
    total_waste_gap_dollars: float
    headline_lift_pct: float
    headline_left_on_table_annual: float


# ---------------------------------------------------------------------------
# Seed data generator
# ---------------------------------------------------------------------------

_CAMPAIGNS: list[tuple[str, Role]] = [
    ("SEM Brand", Role.DEFEND),
    ("SEM Non-Brand", Role.SCALE),
    ("Paid Social - Prospecting", Role.SCALE),
    ("Paid Social - Retargeting", Role.MAINTAIN),
    ("Display Programmatic", Role.SCALE),
    ("YouTube Pre-roll", Role.SCALE),
    ("Direct Mail - Acquisition", Role.EXPERIMENT),
    ("Email CRM Reactivation", Role.MAINTAIN),
    ("Connected TV", Role.EXPERIMENT),
    ("Affiliate / Partnerships", Role.DEFEND),
]

_DMAS: list[str] = [
    "Cincinnati, OH",
    "Chicago, IL",
    "Columbus, OH",
    "Atlanta, GA",
    "Nashville, TN",
    "Charlotte, NC",
]


def generate_seed_combos() -> list[Combo]:
    """Generate 60 deterministic campaign x DMA combos with fitted curves.

    Uses seed=42 so outputs are reproducible.  The response-curve
    parameters (k, s_ref) and current spend are drawn from plausible
    distributions shaped to mirror a mid-size bank's paid-media
    portfolio.
    """
    rng = np.random.default_rng(_RNG_SEED)
    combos: list[Combo] = []

    for campaign_name, role in _CAMPAIGNS:
        # Base spend varies by role
        base_spend_map = {
            Role.SCALE: 30_000,
            Role.DEFEND: 22_000,
            Role.MAINTAIN: 15_000,
            Role.EXPERIMENT: 8_000,
        }
        base_spend = base_spend_map[role]

        # k and s_ref vary by campaign type to create different curve shapes
        base_k = rng.uniform(80, 350)
        base_s_ref = rng.uniform(8_000, 50_000)

        for dma in _DMAS:
            # Add DMA-level variation
            dma_mult = rng.uniform(0.6, 1.4)
            k = base_k * dma_mult
            s_ref = base_s_ref * rng.uniform(0.7, 1.3)

            # Current spend with noise
            current_spend = base_spend * dma_mult * rng.uniform(0.8, 1.2)
            current_spend = max(current_spend, 1_000)  # floor at $1k

            # Account value varies slightly by DMA / campaign
            account_value = rng.uniform(280, 420)

            combos.append(Combo(
                campaign=campaign_name,
                dma=dma,
                role=role,
                current_spend=round(current_spend, 2),
                k=round(k, 4),
                s_ref=round(s_ref, 2),
                account_value=round(account_value, 2),
            ))

    return combos


# ---------------------------------------------------------------------------
# Optimizer
# ---------------------------------------------------------------------------

def _solve_allocation(
    combos: list[Combo],
    budget: float,
    objective: Objective,
) -> list[float]:
    """Solve for the optimal spend vector via bisection on the Lagrange
    multiplier (lambda) for the budget constraint.

    For PROFIT: at the optimum every combo has the same marginal profit
    (or is at a bound).  For VOLUME: every combo has the same marginal
    response.

    Returns the optimal spend per combo (same ordering as *combos*).
    """
    n = len(combos)
    lo_bounds = np.array([c.spend_lo for c in combos])
    hi_bounds = np.array([c.spend_hi for c in combos])

    def _optimal_spend_at_lambda(lam: float) -> np.ndarray:
        """Given dual variable *lam*, compute the unconstrained optimal
        spend for each combo then clip to bounds."""
        spends = np.empty(n)
        for i, c in enumerate(combos):
            if objective == Objective.PROFIT:
                # marginal profit = account_value * k / (s_ref + spend) - 1 = lam
                # => spend = account_value * k / (1 + lam) - s_ref
                denom = 1.0 + lam
                if denom <= 0:
                    spends[i] = hi_bounds[i]
                else:
                    s = c.account_value * c.k / denom - c.s_ref
                    spends[i] = s
            else:
                # marginal response = k / (s_ref + spend) = lam
                # => spend = k / lam - s_ref
                if lam <= 0:
                    spends[i] = hi_bounds[i]
                else:
                    s = c.k / lam - c.s_ref
                    spends[i] = s

        return np.clip(spends, lo_bounds, hi_bounds)

    # Bisection: find lambda such that sum(spend) == budget
    lam_lo, lam_hi = -10.0, 100.0

    # Expand search range if needed
    for _ in range(20):
        if _optimal_spend_at_lambda(lam_lo).sum() < budget:
            lam_lo *= 2
        if _optimal_spend_at_lambda(lam_hi).sum() > budget:
            lam_hi *= 2

    for _ in range(200):
        lam_mid = (lam_lo + lam_hi) / 2.0
        total = _optimal_spend_at_lambda(lam_mid).sum()
        if abs(total - budget) < 1.0:  # within $1
            break
        if total > budget:
            lam_lo = lam_mid
        else:
            lam_hi = lam_mid

    optimal_spends = _optimal_spend_at_lambda((lam_lo + lam_hi) / 2.0)

    # Final budget normalization — scale proportionally to match exactly
    total = optimal_spends.sum()
    if total > 0 and abs(total - budget) > 1.0:
        optimal_spends = optimal_spends * (budget / total)
        optimal_spends = np.clip(optimal_spends, lo_bounds, hi_bounds)

    return optimal_spends.tolist()


def run_optimization(
    combos: list[Combo] | None = None,
    objective: Objective = Objective.PROFIT,
    budget: float | None = None,
) -> OptimizationResult:
    """Run the Next-Best-Dollar allocator.

    Parameters
    ----------
    combos : list[Combo] | None
        The campaign x DMA combos.  Defaults to seed data.
    objective : Objective
        ``"profit"`` maximizes contribution margin; ``"volume"``
        maximizes total accounts.
    budget : float | None
        Total weekly budget to allocate.  Defaults to the sum of
        current spend across all combos (budget-neutral reallocation).

    Returns
    -------
    OptimizationResult
        Full optimization output including per-combo allocations,
        top reallocation moves, and headline metrics.
    """
    if combos is None:
        combos = generate_seed_combos()

    if budget is None:
        budget = sum(c.current_spend for c in combos)

    optimal_spends = _solve_allocation(combos, budget, objective)

    # Build per-combo results
    allocations: list[OptimalAllocation] = []
    for i, c in enumerate(combos):
        opt_spend = optimal_spends[i]
        opt_accounts = c.response(opt_spend)
        cur_profit = c.profit(c.current_spend)
        opt_profit = c.profit(opt_spend)

        waste_accts = opt_accounts - c.current_accounts
        waste_dollars = opt_profit - cur_profit

        delta = opt_spend - c.current_spend
        delta_pct = (delta / c.current_spend * 100) if c.current_spend > 0 else 0.0

        allocations.append(OptimalAllocation(
            campaign=c.campaign,
            dma=c.dma,
            role=c.role.value,
            current_spend=round(c.current_spend, 2),
            optimal_spend=round(opt_spend, 2),
            current_accounts=round(c.current_accounts, 1),
            optimal_accounts=round(opt_accounts, 1),
            current_profit=round(cur_profit, 2),
            optimal_profit=round(opt_profit, 2),
            waste_gap_accounts=round(waste_accts, 1),
            waste_gap_dollars=round(waste_dollars, 2),
            delta_spend=round(delta, 2),
            delta_pct=round(delta_pct, 1),
        ))

    # Top moves — sort by absolute waste-gap $ improvement, pair donors
    # with recipients
    sorted_allocs = sorted(allocations, key=lambda a: a.waste_gap_dollars, reverse=True)
    donors = [a for a in sorted_allocs if a.delta_spend < -100]
    recipients = [a for a in sorted_allocs if a.delta_spend > 100]

    # Sort donors by largest cut, recipients by largest gain
    donors.sort(key=lambda a: a.delta_spend)
    recipients.sort(key=lambda a: a.delta_spend, reverse=True)

    top_moves: list[MoveRecommendation] = []
    for i in range(min(len(donors), len(recipients), 10)):
        d = donors[i]
        r = recipients[i]
        delta_amt = min(abs(d.delta_spend), abs(r.delta_spend))

        # Compute ROAS impact as the marginal improvement
        roas_impact = round(r.waste_gap_dollars / delta_amt, 2) if delta_amt > 0 else 0.0

        rationale = _generate_rationale(d, r)

        top_moves.append(MoveRecommendation(
            from_campaign=f"{d.campaign} ({d.dma})",
            from_dma=d.dma,
            to_campaign=f"{r.campaign} ({r.dma})",
            to_dma=r.dma,
            delta=round(delta_amt, 2),
            rationale=rationale,
            roas_impact=roas_impact,
        ))

    # Headline metrics
    total_cur_spend = sum(c.current_spend for c in combos)
    total_opt_spend = sum(a.optimal_spend for a in allocations)
    total_cur_accts = sum(c.current_accounts for c in combos)
    total_opt_accts = sum(a.optimal_accounts for a in allocations)
    total_cur_profit = sum(c.profit(c.current_spend) for c in combos)
    total_opt_profit = sum(a.optimal_profit for a in allocations)
    total_waste = sum(max(0, a.waste_gap_dollars) for a in allocations)

    lift_pct = ((total_opt_accts - total_cur_accts) / total_cur_accts * 100
                if total_cur_accts > 0 else 0.0)

    # Annualize the waste gap (weekly -> 52 weeks)
    left_on_table_annual = total_waste * 52

    return OptimizationResult(
        objective=objective.value,
        budget=round(budget, 2),
        allocations=allocations,
        top_moves=top_moves,
        total_current_spend=round(total_cur_spend, 2),
        total_optimal_spend=round(total_opt_spend, 2),
        total_current_accounts=round(total_cur_accts, 1),
        total_optimal_accounts=round(total_opt_accts, 1),
        total_current_profit=round(total_cur_profit, 2),
        total_optimal_profit=round(total_opt_profit, 2),
        total_waste_gap_dollars=round(total_waste, 2),
        headline_lift_pct=round(lift_pct, 1),
        headline_left_on_table_annual=round(left_on_table_annual, 2),
    )


def _generate_rationale(donor: OptimalAllocation, recipient: OptimalAllocation) -> str:
    """Generate a human-readable rationale for a reallocation move."""
    if recipient.role == "Scale":
        return (
            f"Scale campaign in {recipient.dma} has steeper marginal curve; "
            f"each shifted $ yields {abs(recipient.waste_gap_accounts):.0f} "
            f"incremental accounts"
        )
    if donor.role == "Experiment":
        return (
            f"Experiment in {donor.dma} saturated — marginal return flat; "
            f"reallocating to higher-response {recipient.campaign}"
        )
    if recipient.role == "Defend":
        return (
            f"Defend campaign under-invested in {recipient.dma}; "
            f"reallocating from over-pacing {donor.campaign}"
        )
    return (
        f"Marginal ROI in {recipient.campaign} ({recipient.dma}) "
        f"exceeds {donor.campaign} ({donor.dma}) by "
        f"{abs(recipient.waste_gap_dollars - donor.waste_gap_dollars):,.0f}/wk"
    )


# ---------------------------------------------------------------------------
# Waste-gap analysis
# ---------------------------------------------------------------------------

def compute_waste_gap(combos: list[Combo] | None = None) -> list[dict]:
    """Compute waste-gap for each combo at its current spend.

    Returns a list of dicts with current vs optimal account yield
    and the dollars left on the table.
    """
    if combos is None:
        combos = generate_seed_combos()

    result = run_optimization(combos)
    return [
        {
            "campaign": a.campaign,
            "dma": a.dma,
            "role": a.role,
            "current_spend": a.current_spend,
            "current_accounts": a.current_accounts,
            "optimal_accounts": a.optimal_accounts,
            "waste_gap_accounts": a.waste_gap_accounts,
            "waste_gap_dollars": a.waste_gap_dollars,
        }
        for a in result.allocations
    ]


# ---------------------------------------------------------------------------
# Rollout simulation
# ---------------------------------------------------------------------------

def simulate_rollout(
    combos: list[Combo] | None = None,
    objective: Objective = Objective.PROFIT,
    budget: float | None = None,
) -> list[RolloutDay]:
    """Simulate a 30-day rollout from current allocation to optimal.

    Each week, spend for each combo moves at most 20% toward its
    optimal target.  Returns daily snapshots with interpolated
    metrics.
    """
    if combos is None:
        combos = generate_seed_combos()

    result = run_optimization(combos, objective, budget)

    current_spends = np.array([c.current_spend for c in combos])
    optimal_spends = np.array([a.optimal_spend for a in result.allocations])

    snapshots: list[RolloutDay] = []

    # Week 0 starts at current
    week_spends = current_spends.copy()

    for day in range(ROLLOUT_DAYS + 1):
        week = day // 7

        if day > 0 and day % 7 == 0 and week <= ROLLOUT_WEEKS:
            # Apply weekly adjustment — move each combo up to 20% toward
            # its target
            for i in range(len(combos)):
                target = optimal_spends[i]
                current = week_spends[i]
                gap = target - current
                max_change = current * MAX_WEEKLY_CHANGE
                if abs(gap) <= max_change:
                    week_spends[i] = target
                else:
                    week_spends[i] = current + math.copysign(max_change, gap)

        # Interpolate within the week for smooth daily values
        if day % 7 == 0:
            day_spends = week_spends.copy()
        else:
            # Linear interpolation within the current week
            week_start = (day // 7) * 7
            frac = (day - week_start) / 7.0
            prev_spends = week_spends.copy()
            # Next week target
            next_target = np.empty_like(week_spends)
            for i in range(len(combos)):
                target = optimal_spends[i]
                current = week_spends[i]
                gap = target - current
                max_change = current * MAX_WEEKLY_CHANGE
                if abs(gap) <= max_change:
                    next_target[i] = target
                else:
                    next_target[i] = current + math.copysign(max_change, gap)
            day_spends = prev_spends + frac * (next_target - prev_spends)

        # Compute daily totals
        total_spend = float(day_spends.sum())
        total_accounts = sum(
            combos[i].response(float(day_spends[i]))
            for i in range(len(combos))
        )
        total_profit = sum(
            combos[i].response(float(day_spends[i])) * combos[i].account_value
            - float(day_spends[i])
            for i in range(len(combos))
        )

        pct_progress = day / ROLLOUT_DAYS * 100

        snapshots.append(RolloutDay(
            day=day,
            total_spend=round(total_spend, 2),
            total_accounts=round(total_accounts, 1),
            total_profit=round(total_profit, 2),
            pct_progress=round(pct_progress, 1),
        ))

    return snapshots


# ---------------------------------------------------------------------------
# Curve data for visualization
# ---------------------------------------------------------------------------

def get_curve_data(combos: list[Combo] | None = None) -> list[dict]:
    """Return response-curve parameters + sample points for each combo.

    Used by the front end to draw the diminishing-returns curves with
    the current-spend dot and optimal-spend ring.
    """
    if combos is None:
        combos = generate_seed_combos()

    result = run_optimization(combos)
    alloc_map = {
        (a.campaign, a.dma): a for a in result.allocations
    }

    curves: list[dict] = []
    for c in combos:
        alloc = alloc_map.get((c.campaign, c.dma))

        # Sample the curve at multiple points for drawing
        max_spend = c.current_spend * 3.0
        sample_spends = np.linspace(0, max_spend, 50)
        sample_accounts = [round(c.response(float(s)), 2) for s in sample_spends]

        curves.append({
            "campaign": c.campaign,
            "dma": c.dma,
            "role": c.role.value,
            "k": c.k,
            "s_ref": c.s_ref,
            "current_spend": c.current_spend,
            "current_accounts": round(c.current_accounts, 2),
            "optimal_spend": alloc.optimal_spend if alloc else c.current_spend,
            "optimal_accounts": alloc.optimal_accounts if alloc else c.current_accounts,
            "account_value": c.account_value,
            "spend_lo": round(c.spend_lo, 2),
            "spend_hi": round(c.spend_hi, 2),
            "curve_samples": {
                "spend": [round(float(s), 2) for s in sample_spends],
                "accounts": sample_accounts,
            },
        })

    return curves
