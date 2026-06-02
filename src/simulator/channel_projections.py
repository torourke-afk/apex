"""
Channel Mix Projection Engine
------------------------------
Computes projected media performance metrics from a brand media channel mix.

Coefficients are seeded from internal planning benchmarks (seed data).
All calculations are pure-Python and run in <500 ms.
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Seed coefficients (internal planning benchmarks)
# Units per 1 percentage point of budget allocated to the channel:
#   impressions_per_point  — impressions delivered per $1M base budget per pt
#   reach_pct_per_point    — net reach % of target audience per pt
#   leads_per_point        — qualified lead units per pt
#   cpm                    — effective CPM ($) at the channel's typical scale
# ---------------------------------------------------------------------------

CHANNEL_COEFFICIENTS: dict[str, dict] = {
    "ctv_olv": {
        "label": "CTV / OLV",
        "impressions_per_point": 420_000,   # high-volume video
        "reach_pct_per_point": 0.85,
        "leads_per_point": 18,
        "cpm": 22.50,
        "color": "#800000",   # Mahogany
    },
    "paid_social": {
        "label": "Paid Social",
        "impressions_per_point": 680_000,   # lower CPM, higher vol
        "reach_pct_per_point": 1.10,
        "leads_per_point": 32,
        "cpm": 12.80,
        "color": "#FF0016",   # RVGT Red
    },
    "audio": {
        "label": "Audio",
        "impressions_per_point": 310_000,   # reach-efficient, lower lead rate
        "reach_pct_per_point": 0.70,
        "leads_per_point": 9,
        "cpm": 8.40,
        "color": "#9BA6B1",   # Iron
    },
}

# Soft-constraint ranges (warn outside, but don't hard-block)
SOFT_CONSTRAINTS: dict[str, tuple[int, int]] = {
    "ctv_olv":     (30, 50),
    "paid_social": (25, 50),
    "audio":       (5,  20),
}

# Default mix (sum = 90%; remaining 10% is "other / unallocated")
DEFAULT_MIX: dict[str, int] = {
    "ctv_olv":     40,
    "paid_social": 35,
    "audio":       10,
}

# Base budget for projections ($M) — overridden by session_state when available
DEFAULT_BASE_BUDGET_M: float = 5.0


# ---------------------------------------------------------------------------
# Projection calculation
# ---------------------------------------------------------------------------

@dataclass
class ChannelProjection:
    channel_key: str
    label: str
    allocation_pct: int
    impressions: int
    reach_pct: float
    leads: int
    spend_m: float
    cpm: float
    color: str


@dataclass
class MixProjection:
    channels: list[ChannelProjection]
    total_impressions: int
    total_reach_pct: float   # capped at 100 — channels share audience
    total_leads: int
    blended_cpm: float
    total_allocated_pct: int
    unallocated_pct: int
    base_budget_m: float
    warnings: list[str]


def compute_projections(
    mix: dict[str, int],
    base_budget_m: float = DEFAULT_BASE_BUDGET_M,
) -> MixProjection:
    """
    Compute channel-level and aggregate projections for a given channel mix.

    Parameters
    ----------
    mix : dict[str, int]
        Keys are channel keys (e.g. "ctv_olv"), values are integer percentages.
    base_budget_m : float
        Total brand media budget in $M used to scale absolute projections.

    Returns
    -------
    MixProjection
        Dataclass with per-channel and aggregate projection metrics.
    """
    channels: list[ChannelProjection] = []
    total_impressions = 0
    total_leads = 0
    total_weighted_cpm = 0.0
    total_allocated_pct = sum(mix.values())
    warnings: list[str] = []

    for key, coef in CHANNEL_COEFFICIENTS.items():
        pct = mix.get(key, 0)
        spend_m = base_budget_m * (pct / 100)

        impressions = int(coef["impressions_per_point"] * pct * base_budget_m)
        reach_pct = coef["reach_pct_per_point"] * pct
        leads = int(coef["leads_per_point"] * pct * base_budget_m)

        total_impressions += impressions
        total_leads += leads
        total_weighted_cpm += coef["cpm"] * pct

        channels.append(
            ChannelProjection(
                channel_key=key,
                label=coef["label"],
                allocation_pct=pct,
                impressions=impressions,
                reach_pct=round(reach_pct, 1),
                leads=leads,
                spend_m=round(spend_m, 2),
                cpm=coef["cpm"],
                color=coef["color"],
            )
        )

    # Blended CPM weighted by allocation share (avoid div-by-zero)
    blended_cpm = (
        total_weighted_cpm / total_allocated_pct if total_allocated_pct > 0 else 0.0
    )

    # Reach cap — channels share overlapping audiences; cap at 95%
    raw_reach = sum(c.reach_pct for c in channels)
    total_reach_pct = round(min(raw_reach, 95.0), 1)

    # Soft-constraint warnings
    for key, (lo, hi) in SOFT_CONSTRAINTS.items():
        pct = mix.get(key, 0)
        label = CHANNEL_COEFFICIENTS[key]["label"]
        if pct < lo:
            warnings.append(
                f"{label} is below the recommended minimum of {lo}% "
                f"(currently {pct}%). Consider increasing allocation."
            )
        elif pct > hi:
            warnings.append(
                f"{label} exceeds the recommended maximum of {hi}% "
                f"(currently {pct}%). Consider rebalancing."
            )

    if total_allocated_pct > 100:
        warnings.append(
            f"Total allocation is {total_allocated_pct}% — reduce by "
            f"{total_allocated_pct - 100} percentage point(s) to stay within budget."
        )

    return MixProjection(
        channels=channels,
        total_impressions=total_impressions,
        total_reach_pct=total_reach_pct,
        total_leads=total_leads,
        blended_cpm=round(blended_cpm, 2),
        total_allocated_pct=total_allocated_pct,
        unallocated_pct=max(0, 100 - total_allocated_pct),
        base_budget_m=base_budget_m,
        warnings=warnings,
    )
