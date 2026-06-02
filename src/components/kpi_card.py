"""
KPI Card Component
------------------
Reusable card for displaying a single metric with optional delta and sparkline.
"""

from __future__ import annotations

import re

import streamlit as st
import plotly.graph_objects as go

from src.config.brand import COLORS, TYPOGRAPHY, BORDER_RADIUS, MOTION, GRADIENTS


def _format_value(value: float, format_type: str) -> str:
    """Format a numeric value according to the specified type."""
    if format_type == "currency":
        if abs(value) >= 1_000_000:
            return f"${value / 1_000_000:,.1f}M"
        if abs(value) >= 1_000:
            return f"${value / 1_000:,.1f}K"
        if value == int(value):
            return f"${value:,.0f}"
        return f"${value:,.2f}"
    if format_type == "percent":
        return f"{value:.1f}%"
    if format_type == "number":
        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:,.1f}M"
        if abs(value) >= 1_000:
            return f"{value / 1_000:,.1f}K"
        return f"{value:,.0f}"
    # fallback — plain number
    return f"{value:,.0f}"


def _sparkline_fig(data: list[float]) -> go.Figure:
    """Build a minimal inline Plotly sparkline figure.

    Color reflects trend direction using gradient-style colors:
    - blue→cyan gradient for improving
    - red for declining
    - amber for flat
    """
    if data[-1] > data[0]:
        line_color = COLORS["secondary"]  # blue
    elif data[-1] < data[0]:
        line_color = COLORS["error"]
    else:
        line_color = COLORS["warning"]
    r, g, b = int(line_color[1:3], 16), int(line_color[3:5], 16), int(line_color[5:7], 16)
    fill_color = f"rgba({r},{g},{b},0.18)"

    fig = go.Figure(
        go.Scatter(
            y=data,
            mode="lines",
            line=dict(color=line_color, width=2, shape="spline"),
            fill="tozeroy",
            fillcolor=fill_color,
            hoverinfo="skip",
        )
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False, showgrid=False, zeroline=False),
        yaxis=dict(visible=False, showgrid=False, zeroline=False),
        height=60,
        showlegend=False,
    )
    return fig


# Map caller-facing severity names to alert_badge severity values
_ALERT_STATUS_MAP: dict[str, str] = {
    "critical": "error",
    "warning": "warning",
    "info": "info",
    "success": "success",
    "error": "error",
}


def kpi_card(
    title: str,
    value: float,
    delta: float = None,
    delta_pct: float = None,
    sparkline_data: list = None,
    format_type: str = "number",
    alert_status: str | None = None,
    alert_text: str | None = None,
    icon: str | None = None,
    invert_delta: bool = False,
) -> None:
    """
    Render a branded KPI card.

    Parameters
    ----------
    title : str
        Metric label displayed above the value.
    value : float
        The primary metric value.
    delta : float, optional
        Absolute change vs prior period.
    delta_pct : float, optional
        Percentage change vs prior period (shown alongside delta).
    sparkline_data : list of float, optional
        7–12 data points for the inline trend chart.
    format_type : str
        One of ``"number"``, ``"currency"``, or ``"percent"``.
    alert_status : str, optional
        When set, renders an alert badge in the card header.
        One of ``"critical"``, ``"warning"``, ``"info"``, ``"success"``, ``"error"``.
    alert_text : str, optional
        When set, renders a red border on the card and displays this text as an
        intervention label beneath the value row.
        If ``alert_status`` is not also provided, defaults the badge severity to
        ``"warning"``.
    icon : str, optional
        Emoji or HTML icon string displayed beside the metric label (e.g. ``"💰"``).
    invert_delta : bool
        When ``True``, a positive delta is colored red (bad) and a negative delta
        green (good). Use for cost metrics like CPIHH and CAC where lower is better.
    """
    # Lazily import badge_html to avoid circular import in tests
    from src.components.alert_badge import badge_html

    glass_bg = COLORS["glass_bg"]
    glass_border = COLORS["glass_border"]
    surface = COLORS["surface"]
    border = COLORS["error"] if alert_text else glass_border
    border_width = "2px" if alert_text else "1px"
    text_primary = COLORS["text_primary"]
    text_secondary = COLORS["text_secondary"]
    success = COLORS["success"]
    error = COLORS["error"]
    font = TYPOGRAPHY["font_family"]
    radius = BORDER_RADIUS["xl"]  # 20px — Vision UI style
    t_fast = MOTION["duration_fast"]
    t_normal = MOTION["duration_normal"]
    ease_out = MOTION["ease_out"]

    has_sparkline = bool(sparkline_data and len(sparkline_data) >= 2)

    # bottom radius is 0 when sparkline will be attached below
    bottom_radius = "0" if has_sparkline else radius

    formatted_value = _format_value(value, format_type)

    # --- scoped CSS class for hover (unique per title) ---
    safe_id = re.sub(r"[^a-z0-9]", "-", title.lower())
    card_class = f"apex-kpi-card apex-kpi-{safe_id}"

    # --- delta display ---
    delta_html = ""
    if delta is not None:
        positive = delta >= 0
        arrow = "▲" if positive else "▼"
        if invert_delta:
            delta_color = error if positive else success
        else:
            delta_color = success if positive else error
        delta_str = _format_value(abs(delta), format_type)
        pct_str = f" ({abs(delta_pct):.1f}%)" if delta_pct is not None else ""
        delta_html = (
            f'<span style="color:{delta_color};font-size:0.8rem;font-weight:600;">'
            f"{arrow} {delta_str}{pct_str}"
            f"</span>"
        )

    # --- icon slot ---
    icon_html = (
        f'<span style="margin-right:0.3rem;font-size:0.75rem;line-height:1;">{icon}</span>'
        if icon
        else ""
    )

    # --- alert badge (embedded inside card header row) ---
    badge = ""
    effective_status = alert_status or ("warning" if alert_text else None)
    if effective_status is not None:
        severity = _ALERT_STATUS_MAP.get(effective_status, effective_status)
        badge_label = alert_text if alert_text else effective_status.upper()
        badge = badge_html(text=badge_label, severity=severity)

    # --- Kamino intervention text row (shown only when alert_text is set) ---
    intervention_html = ""
    if alert_text:
        intervention_html = f"""
  <div style="
      margin-top: 0.6rem;
      padding: 0.4rem 0.6rem;
      background-color: rgba(227, 26, 26, 0.12);
      border-left: 3px solid {error};
      border-radius: 0 4px 4px 0;
      font-size: 0.72rem;
      font-weight: 600;
      color: {error};
      font-family: {font};
  ">{alert_text}</div>"""

    # Inject scoped hover CSS — glassmorphism glow on hover
    hover_css = f"""<style>
  .apex-kpi-card {{
    transition: box-shadow {t_normal} {ease_out}, transform {t_fast} {ease_out};
  }}
  .apex-kpi-card:hover {{
    box-shadow: 0 8px 32px rgba(0, 117, 255, 0.15) !important;
    transform: translateY(-2px) !important;
  }}
</style>"""

    card_html = f"""{hover_css}
<div class="{card_class}" style="
    background: {glass_bg};
    border: {border_width} solid {border};
    border-radius: {radius} {radius} {bottom_radius} {bottom_radius};
    padding: 1.25rem 1.5rem 1rem;
    font-family: {font};
    min-width: 0;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
">
  <div style="
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 0.35rem;
  ">
    <span style="
        display: flex;
        align-items: center;
        color: {text_secondary};
        font-size: 0.65rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.07em;
    ">{icon_html}{title}</span>
    {badge}
  </div>
  <div style="
      color: {text_primary};
      font-size: 1.9rem;
      font-weight: 700;
      line-height: 1.15;
      letter-spacing: -0.02em;
      margin-bottom: 0.3rem;
      white-space: nowrap;
  ">{formatted_value}</div>
  {delta_html}
  {intervention_html}
</div>
"""

    with st.container():
        st.markdown(card_html, unsafe_allow_html=True)
        if has_sparkline:
            fig = _sparkline_fig(sparkline_data)
            st.markdown(
                f'<div style="'
                f'margin-top:-0.6rem;'
                f'border:{border_width} solid {glass_border};'
                f'border-top:none;'
                f'border-radius:0 0 {radius} {radius};'
                f'background:{glass_bg};'
                f'backdrop-filter:blur(12px);'
                f'-webkit-backdrop-filter:blur(12px);'
                f'overflow:hidden;'
                f'line-height:0;'
                f'">',
                unsafe_allow_html=True,
            )
            st.plotly_chart(
                fig,
                use_container_width=True,
                config={"displayModeBar": False, "staticPlot": True},
                key=f"spark_{title.lower().replace(' ', '_')}",
            )
            st.markdown("</div>", unsafe_allow_html=True)
