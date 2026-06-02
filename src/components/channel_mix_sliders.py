"""
Channel Mix Sliders Component
------------------------------
Interactive st.slider() controls for brand media channel mix with:
- Soft-constraint warnings when allocations exceed recommended ranges
- Real-time projection recalculation (<500 ms)
- Persistent state via st.session_state
"""

from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go

from src.config.brand import COLORS, TYPOGRAPHY
from src.simulator.channel_projections import (
    CHANNEL_COEFFICIENTS,
    DEFAULT_MIX,
    DEFAULT_BASE_BUDGET_M,
    SOFT_CONSTRAINTS,
    compute_projections,
    MixProjection,
)

# Session-state key prefix
_SS_PREFIX = "channel_mix_"
_SS_BUDGET = "channel_mix_budget_m"


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def _init_state() -> None:
    """Seed session_state with defaults on first load."""
    for key, default_pct in DEFAULT_MIX.items():
        ss_key = f"{_SS_PREFIX}{key}"
        if ss_key not in st.session_state:
            st.session_state[ss_key] = default_pct
    if _SS_BUDGET not in st.session_state:
        st.session_state[_SS_BUDGET] = DEFAULT_BASE_BUDGET_M


def _read_mix() -> dict[str, int]:
    return {
        key: int(st.session_state.get(f"{_SS_PREFIX}{key}", DEFAULT_MIX[key]))
        for key in CHANNEL_COEFFICIENTS
    }


# ---------------------------------------------------------------------------
# Sub-renders
# ---------------------------------------------------------------------------

def _render_donut(projection: MixProjection) -> None:
    """Small donut chart showing current mix allocation."""
    labels = [c.label for c in projection.channels]
    values = [c.allocation_pct for c in projection.channels]
    colors = [c.color for c in projection.channels]

    unalloc = projection.unallocated_pct
    if unalloc > 0:
        labels.append("Unallocated")
        values.append(unalloc)
        colors.append(COLORS["alloy"])

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.60,
            marker=dict(colors=colors, line=dict(color=COLORS["surface"], width=2)),
            textinfo="label+percent",
            textfont=dict(family=TYPOGRAPHY["font_family"], size=11, color=COLORS["text_primary"]),
            hovertemplate="%{label}: %{value}%<extra></extra>",
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=8, b=0),
        height=220,
        showlegend=False,
        annotations=[
            dict(
                text=f"<b>{projection.total_allocated_pct}%</b><br><span style='font-size:10px'>allocated</span>",
                x=0.5, y=0.5,
                font=dict(family=TYPOGRAPHY["font_family"], size=14, color=COLORS["text_primary"]),
                showarrow=False,
            )
        ],
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _metric_html(label: str, value: str) -> str:
    """Render a compact projection metric as HTML."""
    return (
        f'<div style="text-align:center;padding:0.5rem 0;">'
        f'<div style="color:{COLORS["text_secondary"]};font-size:0.65rem;font-weight:600;'
        f'text-transform:uppercase;letter-spacing:0.06em;">{label}</div>'
        f'<div style="color:{COLORS["text_primary"]};font-size:1.25rem;font-weight:700;'
        f'line-height:1.2;margin-top:0.15rem;">{value}</div>'
        f'</div>'
    )


def _render_projection_strip(projection: MixProjection) -> None:
    """Four-up metric strip for projected outcomes."""
    def fmt_impressions(n: int) -> str:
        if n >= 1_000_000_000:
            return f"{n / 1_000_000_000:.1f}B"
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n / 1_000:.0f}K"
        return str(n)

    cols = st.columns(4)
    metrics = [
        ("Proj. Impressions", fmt_impressions(projection.total_impressions)),
        ("Proj. Reach", f"{projection.total_reach_pct}%"),
        ("Proj. Leads", f"{projection.total_leads:,}"),
        ("Blended CPM", f"${projection.blended_cpm:.2f}"),
    ]
    for col, (label, val) in zip(cols, metrics):
        with col:
            st.markdown(_metric_html(label, val), unsafe_allow_html=True)


def _render_channel_bar(projection: MixProjection) -> None:
    """Stacked horizontal bar showing spend per channel."""
    fig = go.Figure()
    for ch in projection.channels:
        fig.add_trace(
            go.Bar(
                name=ch.label,
                x=[ch.allocation_pct],
                y=["Mix"],
                orientation="h",
                marker_color=ch.color,
                text=f"{ch.label}<br>{ch.allocation_pct}%",
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(family=TYPOGRAPHY["font_family"], size=11, color=COLORS["surface"]),
                hovertemplate=(
                    f"<b>{ch.label}</b><br>"
                    f"Allocation: {ch.allocation_pct}%<br>"
                    f"Spend: ${ch.spend_m:.2f}M<br>"
                    f"Impressions: {ch.impressions:,}<br>"
                    f"Leads: {ch.leads:,}<extra></extra>"
                ),
            )
        )
    if projection.unallocated_pct > 0:
        fig.add_trace(
            go.Bar(
                name="Unallocated",
                x=[projection.unallocated_pct],
                y=["Mix"],
                orientation="h",
                marker_color=COLORS["alloy"],
                text=f"Other {projection.unallocated_pct}%",
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(family=TYPOGRAPHY["font_family"], size=11, color=COLORS["text_secondary"]),
                hovertemplate="Unallocated: %{x}%<extra></extra>",
            )
        )
    fig.update_layout(
        barmode="stack",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=4, b=0),
        height=56,
        xaxis=dict(range=[0, 100], visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ---------------------------------------------------------------------------
# Public component
# ---------------------------------------------------------------------------

def channel_mix_sliders(
    base_budget_m: float | None = None,
    show_donut: bool = True,
    show_bar: bool = True,
    key_prefix: str = "",
) -> MixProjection:
    """
    Render channel mix sliders, warnings, and projection metrics.

    Persists slider values to ``st.session_state`` so the mix survives
    Streamlit reruns and page navigations.

    Parameters
    ----------
    base_budget_m : float, optional
        Override the base budget (in $M) for projection scaling.
        Defaults to ``st.session_state["channel_mix_budget_m"]`` or 5.0.
    show_donut : bool
        Whether to render the donut allocation chart.
    show_bar : bool
        Whether to render the stacked allocation bar.
    key_prefix : str
        Optional prefix to namespace widget keys (useful when embedding
        the component multiple times on one page).

    Returns
    -------
    MixProjection
        The computed projection for the current slider values.
    """
    _init_state()

    budget = base_budget_m if base_budget_m is not None else st.session_state[_SS_BUDGET]

    # ── Section header ──────────────────────────────────────────────────────
    st.markdown(
        f"<h3 style='color:{COLORS['secondary']};margin-bottom:0.25rem;'>"
        "Channel Mix Simulator</h3>"
        f"<p style='color:{COLORS['text_secondary']};font-size:0.85rem;margin-top:0;'>"
        f"Adjust allocation across brand media channels · Base budget: "
        f"<strong>${budget:.1f}M</strong></p>",
        unsafe_allow_html=True,
    )

    left, right = st.columns([3, 2], gap="large")

    with left:
        st.markdown(
            f"<p style='color:{COLORS['text_secondary']};font-size:0.75rem;"
            f"font-weight:600;text-transform:uppercase;letter-spacing:0.06em;"
            f"margin-bottom:0.5rem;'>Allocation (%)</p>",
            unsafe_allow_html=True,
        )

        current_mix: dict[str, int] = {}

        for key, coef in CHANNEL_COEFFICIENTS.items():
            lo, hi = SOFT_CONSTRAINTS[key]
            ss_key = f"{_SS_PREFIX}{key}"
            slider_key = f"{key_prefix}slider_{key}"

            val = st.slider(
                label=coef["label"],
                min_value=0,
                max_value=100,
                value=st.session_state.get(ss_key, DEFAULT_MIX.get(key, 0)),
                step=1,
                format="%d%%",
                help=f"Recommended range: {lo}–{hi}%",
                key=slider_key,
            )
            # Persist back to canonical session_state key
            st.session_state[ss_key] = val
            current_mix[key] = val

        # Total allocation indicator
        total = sum(current_mix.values())
        total_color = COLORS["error"] if total > 100 else (
            COLORS["success"] if total <= 95 else COLORS["warning"]
        )
        st.markdown(
            f"<div style='margin-top:0.5rem;padding:0.4rem 0.75rem;"
            f"background:{COLORS['surface']};border:1px solid {COLORS['border']};"
            f"border-radius:6px;display:inline-block;'>"
            f"<span style='color:{COLORS['text_secondary']};font-size:0.75rem;'>Total allocated: </span>"
            f"<span style='color:{total_color};font-weight:700;font-size:0.9rem;'>{total}%</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── Compute projections ─────────────────────────────────────────────────
    projection = compute_projections(current_mix, base_budget_m=budget)

    with right:
        if show_donut:
            _render_donut(projection)

    # ── Warnings ────────────────────────────────────────────────────────────
    if projection.warnings:
        for warning in projection.warnings:
            st.warning(warning, icon="⚠️")

    # ── Stacked bar ─────────────────────────────────────────────────────────
    if show_bar:
        st.markdown(
            f"<p style='color:{COLORS['text_secondary']};font-size:0.7rem;"
            f"font-weight:600;text-transform:uppercase;letter-spacing:0.06em;"
            f"margin-bottom:0;'>Budget distribution</p>",
            unsafe_allow_html=True,
        )
        _render_channel_bar(projection)

    # ── Projection strip ────────────────────────────────────────────────────
    st.markdown(
        f"<p style='color:{COLORS['text_secondary']};font-size:0.7rem;"
        f"font-weight:600;text-transform:uppercase;letter-spacing:0.06em;"
        f"margin-top:0.75rem;margin-bottom:0.25rem;'>Projected outcomes</p>",
        unsafe_allow_html=True,
    )
    _render_projection_strip(projection)

    # ── Per-channel detail expander ─────────────────────────────────────────
    with st.expander("Channel breakdown", expanded=False):
        cols = st.columns(len(CHANNEL_COEFFICIENTS))
        for col, ch in zip(cols, projection.channels):
            with col:
                lo, hi = SOFT_CONSTRAINTS[ch.channel_key]
                in_range = lo <= ch.allocation_pct <= hi
                status_color = COLORS["success"] if in_range else COLORS["warning"]
                status_label = "✓ In range" if in_range else "⚠ Out of range"
                _cs = COLORS["surface"]
                _cb = COLORS["border"]
                _cts = COLORS["text_secondary"]
                _ctp = COLORS["text_primary"]
                st.markdown(
                    f"<div style='background:{_cs};border:1px solid "
                    f"{_cb};border-radius:8px;padding:0.75rem;'>"
                    f"<div style='color:{ch.color};font-weight:700;font-size:0.9rem;"
                    f"margin-bottom:0.5rem;'>{ch.label}</div>"
                    f"<div style='font-size:0.75rem;color:{_cts};'>"
                    f"Allocation: <b style='color:{_ctp};'>{ch.allocation_pct}%</b><br>"
                    f"Spend: <b>${ch.spend_m:.2f}M</b><br>"
                    f"Impressions: <b>{ch.impressions:,}</b><br>"
                    f"Leads: <b>{ch.leads:,}</b><br>"
                    f"CPM: <b>${ch.cpm:.2f}</b><br>"
                    f"Reach: <b>{ch.reach_pct}%</b>"
                    f"</div>"
                    f"<div style='margin-top:0.4rem;font-size:0.65rem;color:{status_color};"
                    f"font-weight:600;'>{status_label} ({lo}–{hi}%)</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    return projection
