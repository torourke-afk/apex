"""
Scenario Comparison Component
------------------------------
Side-by-side comparison widget for up to 3 scenarios.
Differences are color-coded: green (better), red (worse).
"""

from __future__ import annotations

import streamlit as st

from src.config.brand import COLORS, TYPOGRAPHY


def _render_scenario_card(
    scenario: dict,
    metrics: list[str],
    baseline: dict | None,
    font: str,
    invert_metrics: set | None = None,
) -> None:
    """Render a single scenario column card with optional diff highlighting."""
    invert_metrics = invert_metrics or set()
    surface = COLORS["surface"]
    border = COLORS["border"]
    text_primary = COLORS["onyx"]
    text_secondary = COLORS["iron"]
    success = COLORS["success"]
    error = COLORS["error"]
    alloy = COLORS["alloy"]

    name = scenario.get("name", "Scenario")
    is_baseline = baseline is None or scenario is baseline

    header_bg = COLORS["secondary"] if is_baseline else surface
    header_color = COLORS["platinum"] if is_baseline else text_primary
    badge_html = (
        '<span style="'
        f'background:{COLORS["primary"]};color:{COLORS["platinum"]};'
        "font-size:0.6rem;font-weight:700;text-transform:uppercase;"
        "letter-spacing:0.08em;padding:0.1rem 0.4rem;border-radius:3px;"
        'margin-left:0.5rem;">BASELINE</span>'
        if is_baseline
        else ""
    )

    rows_html = ""
    for i, metric in enumerate(metrics):
        value = scenario.get(metric)
        if value is None:
            display_val = "—"
            diff_html = ""
        else:
            display_val = _format_metric(value)

            if not is_baseline and baseline is not None:
                base_val = baseline.get(metric)
                diff_html = _diff_badge(value, base_val, success, error, invert=metric in invert_metrics)
            else:
                diff_html = ""

        row_bg = COLORS["background"] if i % 2 == 0 else surface

        rows_html += f"""
<div style="
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:0.55rem 1rem;
    background:{row_bg};
    border-bottom:1px solid {alloy};
">
  <span style="
      color:{text_secondary};
      font-size:0.75rem;
      font-weight:600;
      text-transform:uppercase;
      letter-spacing:0.05em;
  ">{metric}</span>
  <span style="
      color:{text_primary};
      font-size:0.9rem;
      font-weight:700;
      display:flex;
      align-items:center;
      gap:0.4rem;
  ">{display_val}{diff_html}</span>
</div>"""

    card_html = f"""
<div style="
    background:{surface};
    border:1px solid {COLORS['alloy']};
    border-radius:8px;
    overflow:hidden;
    font-family:{font};
    height:100%;
">
  <div style="
      background:{header_bg};
      padding:0.75rem 1rem;
      border-bottom:2px solid {COLORS['primary']};
  ">
    <span style="
        color:{header_color};
        font-size:0.95rem;
        font-weight:700;
    ">{name}</span>{badge_html}
  </div>
  {rows_html}
</div>
"""
    st.markdown(card_html, unsafe_allow_html=True)


def _format_metric(value) -> str:
    """Format a metric value for display."""
    if isinstance(value, float):
        if value != int(value):
            # Show as percent if between -1 and 1, else decimal
            if -1.0 <= value <= 1.0 and value != 0:
                return f"{value * 100:.1f}%"
            return f"{value:,.2f}"
    if isinstance(value, int) or (isinstance(value, float) and value == int(value)):
        v = int(value)
        if abs(v) >= 1_000_000:
            return f"{v / 1_000_000:,.1f}M"
        if abs(v) >= 1_000:
            return f"{v / 1_000:,.1f}K"
        return f"{v:,}"
    return str(value)


def _diff_badge(value, base_val, success_color: str, error_color: str, invert: bool = False) -> str:
    """Return an HTML badge showing the delta vs baseline."""
    if base_val is None or not isinstance(value, (int, float)) or not isinstance(base_val, (int, float)):
        return ""
    if base_val == 0:
        return ""

    delta_pct = (value - base_val) / abs(base_val) * 100
    is_better = (delta_pct >= 0) if not invert else (delta_pct <= 0)
    color = success_color if is_better else error_color
    arrow = "▲" if is_better else "▼"
    sign = "+" if delta_pct >= 0 else ""

    return (
        f'<span style="'
        f"color:{color};font-size:0.7rem;font-weight:700;"
        f'background:{color}18;padding:0.1rem 0.3rem;border-radius:3px;">'
        f"{arrow} {sign}{delta_pct:.1f}%</span>"
    )


def scenario_comparison(
    scenarios: list[dict],
    metrics: list[str],
    invert_metrics: list[str] | None = None,
) -> None:
    """
    Render a side-by-side scenario comparison widget.

    Parameters
    ----------
    scenarios : list[dict]
        Up to 3 scenario dicts. Each should have a ``"name"`` key and
        one key per metric. The first scenario is treated as the baseline.
    metrics : list[str]
        Ordered list of metric keys to display in each scenario card.
    invert_metrics : list[str], optional
        Metrics where lower is better (e.g. ``["CPIHH"]``). For these,
        a decrease is shown green and an increase is shown red.
    """
    invert_metrics = set(invert_metrics or [])
    if not scenarios:
        st.info("No scenarios provided.")
        return

    # Cap at 3 scenarios
    capped = scenarios[:3]
    baseline = capped[0] if capped else None
    font = TYPOGRAPHY["font_family"]

    cols = st.columns(len(capped))
    for col, scenario in zip(cols, capped):
        with col:
            _render_scenario_card(
                scenario=scenario,
                metrics=metrics,
                baseline=baseline if scenario is not baseline else None,
                font=font,
                invert_metrics=invert_metrics,
            )
