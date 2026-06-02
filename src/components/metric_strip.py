"""
metric_strip.py
---------------
Horizontal strip of 3–6 brand-styled metric cards.
"""

from __future__ import annotations

import streamlit as st

from src.config.brand import COLORS, TYPOGRAPHY, SPACING, BORDER_RADIUS


def _format_value(value: str | float, fmt: str | None) -> str:
    """Format a metric value according to the requested format type."""
    if isinstance(value, str):
        return value

    if fmt == "currency":
        if abs(value) >= 1_000_000:
            return f"${value / 1_000_000:,.1f}M"
        if abs(value) >= 1_000:
            return f"${value / 1_000:,.1f}K"
        return f"${value:,.2f}"

    if fmt == "percent":
        return f"{value:.1f}%"

    if fmt == "number":
        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:,.1f}M"
        if abs(value) >= 1_000:
            return f"{value / 1_000:,.1f}K"
        return f"{value:,.0f}"

    # Default: let Python decide
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


def _fmt_delta(val: float) -> str:
    """Compact-format a delta value (e.g., -180000 → -180K)."""
    sign = "+" if val >= 0 else ""
    a = abs(val)
    if a >= 1_000_000:
        return f"{sign}{val / 1_000_000:,.1f}M"
    if a >= 1_000:
        return f"{sign}{val / 1_000:,.0f}K"
    if a >= 100:
        return f"{sign}{val:,.0f}"
    return f"{sign}{val:,.1f}"


def _delta_html(delta: float | None, delta_pct: float | None = None) -> str:
    """Return an HTML div for the delta indicator, or empty string."""
    if delta is None and delta_pct is None:
        return ""

    ref = delta if delta is not None else delta_pct
    color = COLORS["success"] if ref >= 0 else COLORS["error"]
    arrow = "▲" if ref >= 0 else "▼"
    size = TYPOGRAPHY["sizes"]["sm"]
    weight = TYPOGRAPHY["weights"]["semibold"]

    parts = []
    if delta is not None:
        parts.append(_fmt_delta(delta))
    if delta_pct is not None:
        sign = "+" if delta_pct >= 0 else ""
        parts.append(f"({sign}{delta_pct:.1f}%)")

    return (
        f'<div style="color:{color};font-size:{size};font-weight:{weight};'
        f'margin-top:{SPACING["xxs"]};white-space:nowrap;">'
        f"{arrow} {' '.join(parts)}"
        f"</div>"
    )


def metric_strip(metrics: list[dict]) -> None:
    """Render a horizontal strip of metrics.

    Parameters
    ----------
    metrics:
        List of 3–6 dicts, each with:
        - label or name: str  — metric name (both keys accepted)
        - value: str | float  — display value
        - delta: float, optional  — absolute change indicator (positive = good)
        - delta_pct: float, optional  — percentage change (shown alongside delta)
        - format: str, optional  — "currency", "percent", or "number"
    """
    if not metrics:
        return

    n = max(3, min(8, len(metrics)))
    metrics = metrics[:n]

    glass_bg = COLORS["glass_bg"]
    glass_border = COLORS["glass_border"]
    text_p = COLORS["text_primary"]
    text_s = COLORS["text_secondary"]
    ff = TYPOGRAPHY["font_family"]
    radius = BORDER_RADIUS["xl"]

    cols = st.columns(n)

    for col, m in zip(cols, metrics):
        label = str(m.get("label", m.get("name", "")))
        raw_value = m.get("value", "")
        fmt = m.get("format", None)
        delta = m.get("delta", None)
        delta_pct = m.get("delta_pct", None)

        display_value = _format_value(raw_value, fmt)
        delta_html = _delta_html(delta, delta_pct)

        card_html = f"""
<div style="
    background:{glass_bg};
    border:1px solid {glass_border};
    border-radius:{radius};
    padding:1rem 1.25rem;
    font-family:{ff};
    height:100%;
    min-width:120px;
    box-sizing:border-box;
    backdrop-filter:blur(12px);
    -webkit-backdrop-filter:blur(12px);
    transition:box-shadow 250ms cubic-bezier(0.0,0.0,0.2,1);
">
  <div style="
      color:{text_s};
      font-size:0.65rem;
      font-weight:{TYPOGRAPHY['weights']['semibold']};
      text-transform:uppercase;
      letter-spacing:0.08em;
      margin-bottom:{SPACING['xs']};
      white-space:nowrap;
      overflow:hidden;
      text-overflow:ellipsis;
  ">{label}</div>
  <div style="
      color:{text_p};
      font-size:1.35rem;
      font-weight:700;
      line-height:{TYPOGRAPHY['line_height']['tight']};
      white-space:nowrap;
  ">{display_value}</div>
  {delta_html}
</div>
"""
        with col:
            st.markdown(card_html, unsafe_allow_html=True)
