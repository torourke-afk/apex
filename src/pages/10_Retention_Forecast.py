"""
Retention Forecast — Signal Deck spec
Cohort retention heatmap, LTV accrual curve, and KPI deck.
Pure HTML/CSS via st.markdown; no Plotly, no st.columns/st.metric.
"""

import streamlit as st

from src.components.filter_bar import get_global_filters
from src.components.page_chrome import page_chrome
from src.components.chat_drawer import render_chat_drawer

try:
    from src.data.retention_forecast import (
        load_account_data,
        load_fits,
        get_survival_curves,
        get_segment_options,
        get_km_observed,
    )
    from src.data.retention_model_core import shrink_survival, SegmentFit
    _HAS_DEPS = True
except ImportError:
    _HAS_DEPS = False


# ---------------------------------------------------------------------------
# Page chrome
# ---------------------------------------------------------------------------

page_chrome(title="Retention Forecast", category="RETENTION")
filters = get_global_filters()


# ---------------------------------------------------------------------------
# Cohort data (sample / fallback)
# ---------------------------------------------------------------------------

_COHORT_LABELS = [
    "Jan 25", "Feb 25", "Mar 25", "Apr 25",
    "May 25", "Jun 25", "Jul 25", "Aug 25",
]

_COHORT_DATA = [
    [97, 92, 88, 84, 80, 76, 72, 68],
    [96, 91, 87, 83, 79, 75, 71, 67],
    [97, 93, 89, 85, 81, 77, 73, 70],
    [95, 90, 86, 82, 78, 74, 70, 66],
    [96, 92, 88, 84, 80, 76, 72, 69],
    [97, 93, 90, 86, 82, 78, 74, 71],
    [96, 91, 87, 83, 79, 75, 0, 0],
    [97, 93, 89, 85, 0, 0, 0, 0],
]


# ---------------------------------------------------------------------------
# Style block
# ---------------------------------------------------------------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
@keyframes rise { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
@media (prefers-reduced-motion: reduce) { * { animation:none !important; transition:none !important; } }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Build HTML
# ---------------------------------------------------------------------------

_mono = "'JetBrains Mono',monospace"
_ff = "'Space Grotesk',system-ui,sans-serif"


def _heatmap_cell(value: int) -> str:
    """Return an HTML cell for the cohort heatmap."""
    if value == 0:
        return (
            f'<div style="border-radius:4px;padding:5px 3px;text-align:center;'
            f'font-family:{_mono};font-size:10px;font-weight:500;'
            f'color:var(--text3);">—</div>'
        )
    opacity = round(value / 100 * 0.5, 3)
    text_color = "var(--text)" if value >= 75 else "var(--text2)"
    return (
        f'<div style="border-radius:4px;padding:5px 3px;text-align:center;'
        f'font-family:{_mono};font-size:10px;font-weight:500;'
        f'background:rgba(79,216,155,{opacity});color:{text_color};">'
        f'{value}%</div>'
    )


# -- Cohort heatmap rows
heatmap_header = (
    f'<div style="font-family:{_mono};font-size:9px;letter-spacing:.06em;'
    f'color:var(--text3);padding:5px 3px;text-align:center;"></div>'
)
for m in range(1, 9):
    heatmap_header += (
        f'<div style="font-family:{_mono};font-size:9px;letter-spacing:.06em;'
        f'color:var(--text3);padding:5px 3px;text-align:center;">MOB{m}</div>'
    )

heatmap_rows = heatmap_header
for i, label in enumerate(_COHORT_LABELS):
    row_label = (
        f'<div style="font-family:{_mono};font-size:9.5px;color:var(--text2);'
        f'padding:5px 3px;">{label}</div>'
    )
    cells = "".join(_heatmap_cell(v) for v in _COHORT_DATA[i])
    heatmap_rows += row_label + cells


# -- MOB x-axis labels for LTV chart
mob_labels_html = '<div style="display:flex;justify-content:space-between;padding:0 2px;margin-top:4px;">'
for m in range(0, 9):
    lbl = "ACQ" if m == 0 else f"MOB{m * 3}"
    mob_labels_html += (
        f'<span style="font-family:{_mono};font-size:8.5px;'
        f'letter-spacing:.06em;color:var(--text3);">{lbl}</span>'
    )
mob_labels_html += '</div>'


# -- Full HTML
html = f"""
<div style="animation:rise .4s ease-out both;font-family:{_ff};">

  <!-- KPI Cards -->
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:18px;">

    <!-- MOB6 RETENTION -->
    <div style="padding:16px 18px;border-radius:14px;border:1px solid var(--line);background:var(--panel);animation:rise .4s ease-out both;animation-delay:.05s;">
      <div style="font-family:{_mono};font-size:9.5px;letter-spacing:.12em;color:var(--text3);text-transform:uppercase;">MOB6 Retention</div>
      <div style="font-size:26px;font-weight:600;margin-top:6px;color:var(--text);font-family:{_ff};">71.4<span style="font-size:14px;color:var(--text2);">%</span></div>
      <div style="font-family:{_mono};font-size:10px;color:var(--amber);margin-top:3px;">↓ 0.4 vs target 74%</div>
    </div>

    <!-- AVG PORTFOLIO LTV -->
    <div style="padding:16px 18px;border-radius:14px;border:1px solid var(--line);background:var(--panel);animation:rise .4s ease-out both;animation-delay:.1s;">
      <div style="font-family:{_mono};font-size:9.5px;letter-spacing:.12em;color:var(--text3);text-transform:uppercase;">Avg Portfolio LTV</div>
      <div style="font-size:26px;font-weight:600;margin-top:6px;color:var(--text);font-family:{_ff};">$4,180</div>
      <div style="font-family:{_mono};font-size:10px;color:var(--green);margin-top:3px;">↑ 4.5% · target met</div>
    </div>

    <!-- 90-DAY CHURN -->
    <div style="padding:16px 18px;border-radius:14px;border:1px solid var(--line);background:var(--panel);animation:rise .4s ease-out both;animation-delay:.15s;">
      <div style="font-family:{_mono};font-size:9.5px;letter-spacing:.12em;color:var(--text3);text-transform:uppercase;">90-Day Churn</div>
      <div style="font-size:26px;font-weight:600;margin-top:6px;color:var(--text);font-family:{_ff};">8.2<span style="font-size:14px;color:var(--text2);">%</span></div>
      <div style="font-family:{_mono};font-size:10px;color:var(--green);margin-top:3px;">↓ 0.6 pts QoQ</div>
    </div>

    <!-- PAYBACK PERIOD -->
    <div style="padding:16px 18px;border-radius:14px;border:1px solid var(--line);background:var(--panel);animation:rise .4s ease-out both;animation-delay:.2s;">
      <div style="font-family:{_mono};font-size:9.5px;letter-spacing:.12em;color:var(--text3);text-transform:uppercase;">Payback Period</div>
      <div style="font-size:26px;font-weight:600;margin-top:6px;color:var(--text);font-family:{_ff};">9.4<span style="font-size:14px;color:var(--text2);">mo</span></div>
      <div style="font-family:{_mono};font-size:10px;color:var(--text2);margin-top:3px;">CPIHH $312 / LTV curve</div>
    </div>

  </div>

  <!-- Two-column grid: Cohort Retention + LTV Accrual -->
  <div style="display:grid;grid-template-columns:1.2fr 1fr;gap:16px;">

    <!-- LEFT: Cohort Retention Heatmap -->
    <div style="border-radius:14px;border:1px solid var(--line);background:var(--panel);padding:18px;">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">
        <div style="width:3px;height:15px;background:var(--cyan);border-radius:3px;"></div>
        <span style="font-size:14px;font-weight:600;color:var(--text);">Cohort Retention</span>
        <span style="flex:1;"></span>
        <span style="font-family:{_mono};font-size:9px;letter-spacing:.1em;color:var(--text3);">MONTHS ON BOOK →</span>
      </div>
      <div style="display:grid;grid-template-columns:62px repeat(8,1fr);gap:4px;">
        {heatmap_rows}
      </div>
    </div>

    <!-- RIGHT: Cumulative LTV Accrual -->
    <div style="border-radius:14px;border:1px solid var(--line);background:var(--panel);padding:18px;">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">
        <div style="width:3px;height:15px;background:var(--green);border-radius:3px;"></div>
        <span style="font-size:14px;font-weight:600;color:var(--text);">Cumulative LTV Accrual</span>
      </div>
      <div style="font-size:11.5px;color:var(--text3);margin-bottom:6px;">Per-household value vs acquisition cost recovery</div>
      <svg viewBox="0 0 460 220" width="100%" height="220">
        <line x1="0" y1="200" x2="460" y2="200" stroke="var(--line2)" stroke-width="1"/>
        <line x1="0" y1="150" x2="460" y2="150" stroke="var(--line)" stroke-width="1" stroke-dasharray="4 4"/>
        <text x="4" y="146" font-family="'JetBrains Mono',monospace" font-size="9" fill="var(--text3)">CPIHH $312</text>
        <defs>
          <linearGradient id="ltvfill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="var(--green)" stop-opacity="0.25"/>
            <stop offset="1" stop-color="var(--green)" stop-opacity="0"/>
          </linearGradient>
        </defs>
        <path d="M0,200 60,176 120,150 180,124 240,100 300,78 360,58 420,42 460,34 L460,200 L0,200 Z" fill="url(#ltvfill)"/>
        <polyline points="0,200 60,176 120,150 180,124 240,100 300,78 360,58 420,42 460,34" fill="none" stroke="var(--green)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="120" cy="150" r="4" fill="var(--amber)" stroke="var(--bg)" stroke-width="2"/>
        <text x="128" y="166" font-family="'JetBrains Mono',monospace" font-size="9" fill="var(--amber)">breakeven · MOB9</text>
      </svg>
      {mob_labels_html}
    </div>

  </div>

</div>
"""

st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Chat drawer
# ---------------------------------------------------------------------------

render_chat_drawer(page_key="retention_forecast")
