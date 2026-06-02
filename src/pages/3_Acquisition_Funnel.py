"""
Acquisition Funnel — Sankey diagram from Brand UOI → Active (90d)
"""

import math

import streamlit as st
import plotly.graph_objects as go

from src.components.filter_bar import get_global_filters
from src.components.card_container import card_container, card_container_end
from src.config.brand import COLORS, TYPOGRAPHY, BORDER_RADIUS, CHART_PALETTE_EXTENDED
from src.data.funnel_queries import get_funnel_data
from src.components.page_chrome import page_chrome
from src.components.chat_drawer import render_chat_drawer

_RECOVERY_DATA = [
    {"Window": "0–2 hours", "Channel": "Automated email w/ deep link", "Recovery": "Highest", "Manager": "Kamino (auto)"},
    {"Window": "2–24 hours", "Channel": "SMS reminder", "Recovery": "Medium", "Manager": "Kamino (auto)"},
    {"Window": "24–48 hours", "Channel": "Phone / 2nd email", "Recovery": "Medium", "Manager": "Kamino (auto + manual)"},
    {"Window": "48–72 hours", "Channel": "Retargeting ads (dynamic creative)", "Recovery": "Low–Medium", "Manager": "Kamino (auto)"},
    {"Window": "7–14 days", "Channel": "Final email with updated offer", "Recovery": "Low", "Manager": "Kamino (auto)"},
]
_RECOVERY_COLORS = {"Highest": COLORS["success"], "Medium": COLORS["warning"], "Low–Medium": COLORS["warning"], "Low": COLORS["iron"]}

page_chrome(title="Acquisition Funnel")
filters = get_global_filters()
data = get_funnel_data(filters)

stages = data["stages"]
values = data["values"]
benchmarks = data["benchmarks"]
rates = data["rates"]
bench_rates = data["bench_rates"]
avg_ltv = data["avg_account_ltv"]


# ── Helper: log-scale values for visual balance ────────────────────────────
def _log_scale(v: float, floor: float = 1.0) -> float:
    """Log-scale a value so the Sankey is visually readable across 3+ orders of magnitude."""
    return math.log10(max(v, floor)) ** 2  # squaring log10 gives good visual spread


# ── Sankey Diagram ─────────────────────────────────────────────────────────
card_container(title="Acquisition Funnel", subtitle="Flow from Brand UOI → Active accounts — width shows relative conversion, red flows show drop-off")

n_stages = len(stages)
n_transitions = n_stages - 1

# --- Nodes ---
# Stage nodes (0..n_stages-1) + Drop-off nodes (n_stages..n_stages+n_transitions-1)
node_labels = []
for i, s in enumerate(stages):
    node_labels.append(f"{s}  ({values[i]:,.0f})")
for i in range(n_transitions):
    dropped = max(0, values[i] - values[i + 1])
    node_labels.append(f"Drop-off  ({dropped:,.0f})")

_palette = list(CHART_PALETTE_EXTENDED)
stage_colors = [_palette[i % len(_palette)] for i in range(n_stages)]
dropoff_color = "rgba(227, 26, 26, 0.45)"
node_colors = stage_colors + [dropoff_color] * n_transitions

# --- Links (log-scaled for visual balance) ---
sources = []
targets = []
link_values = []
link_colors = []
link_customdata = []

for i in range(n_transitions):
    converted = values[i + 1]
    dropped = max(0, values[i] - values[i + 1])
    dropoff_idx = n_stages + i
    conv_rate = (converted / values[i] * 100) if values[i] > 0 else 0
    drop_rate = (dropped / values[i] * 100) if values[i] > 0 else 0

    # Conversion link
    sources.append(i)
    targets.append(i + 1)
    link_values.append(_log_scale(converted))
    r, g, b = int(stage_colors[i][1:3], 16), int(stage_colors[i][3:5], 16), int(stage_colors[i][5:7], 16)
    link_colors.append(f"rgba({r},{g},{b},0.40)")
    link_customdata.append([stages[i], stages[i + 1], f"{converted:,.0f}", f"{conv_rate:.1f}%"])

    # Drop-off link
    if dropped > 0:
        sources.append(i)
        targets.append(dropoff_idx)
        link_values.append(_log_scale(dropped))
        link_colors.append("rgba(227, 26, 26, 0.25)")
        link_customdata.append([stages[i], "Drop-off", f"{dropped:,.0f}", f"{drop_rate:.1f}%"])

# --- Node positions ---
x_positions = []
y_positions = []
x_start, x_end = 0.005, 0.995
spacing = (x_end - x_start) / max(n_stages - 1, 1)

for i in range(n_stages):
    x_positions.append(x_start + i * spacing)
    # Stagger the last two stage nodes vertically so they don't overlap
    if i == n_stages - 1:
        y_positions.append(0.35)
    else:
        y_positions.append(0.15)
for i in range(n_transitions):
    x_positions.append(x_start + i * spacing + spacing * 0.25)
    y_positions.append(0.88)

fig = go.Figure(go.Sankey(
    arrangement="freeform",
    node=dict(
        pad=30,
        thickness=24,
        line=dict(color=COLORS["glass_border"], width=0.5),
        label=node_labels,
        color=node_colors,
        x=x_positions,
        y=y_positions,
        hovertemplate='<b>%{label}</b><extra></extra>',
    ),
    link=dict(
        source=sources,
        target=targets,
        value=link_values,
        color=link_colors,
        customdata=link_customdata,
        hovertemplate='<b>%{customdata[0]} → %{customdata[1]}</b><br>'
                      'Volume: %{customdata[2]}<br>'
                      'Rate: %{customdata[3]}<extra></extra>',
    ),
))

fig.update_layout(
    height=480,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(
        family=TYPOGRAPHY["font_family"],
        color=COLORS["text_primary"],
        size=11,
    ),
    margin=dict(l=10, r=10, t=15, b=15),
)

st.plotly_chart(fig, use_container_width=True, key="funnel_sankey")
card_container_end()

# ── Drop-off Analysis ──────────────────────────────────────────────────────
card_container(title="Drop-off Analysis", subtitle="Dollar impact of stage friction at each conversion step")
dropoff_cols = st.columns(min(len(stages) - 1, 6))
for i, (rate, bench) in enumerate(zip(rates, bench_rates)):
    if i >= len(dropoff_cols):
        break
    stage_in = values[i]
    stage_out = values[i + 1]
    dropped = stage_in - stage_out
    dollar_impact = dropped * avg_ltv
    delta_vs_bench = rate - bench
    color = COLORS["success"] if delta_vs_bench >= 0 else COLORS["error"]
    with dropoff_cols[i]:
        st.markdown(
            f"""<div style="padding:0.5rem 0;">
            <div style="font-size:0.62rem;font-weight:600;text-transform:uppercase;color:{COLORS['text_secondary']};margin-bottom:0.25rem;">{stages[i][:10]}→{stages[i+1][:10]}</div>
            <div style="font-size:1.4rem;font-weight:700;color:{color};">{rate*100:.1f}%</div>
            <div style="font-size:0.7rem;color:{COLORS['text_secondary']};">Bench: {bench*100:.1f}%</div>
            <div style="font-size:0.7rem;color:{COLORS['error']};margin-top:0.2rem;">-{dropped:,.0f} dropped</div>
            <div style="font-size:0.68rem;color:{COLORS['iron']};">${dollar_impact:,.0f} LTV at risk</div>
            </div>""",
            unsafe_allow_html=True,
        )
card_container_end()

# ── Abandonment Recovery Tracker ───────────────────────────────────────────
card_container(title="Abandonment Recovery Tracker", subtitle="Automated Kamino sequences by recovery window")
hdr = st.columns([1.5, 2.5, 1.5, 2])
for col, h in zip(hdr, ["Window", "Channel", "Recovery", "Managed By"]):
    col.markdown(f"<span style='font-size:0.65rem;font-weight:600;text-transform:uppercase;letter-spacing:0.07em;color:{COLORS['text_secondary']};'>{h}</span>", unsafe_allow_html=True)
st.markdown(f"<hr style='border-color:{COLORS['border']};margin:0.3rem 0;'/>", unsafe_allow_html=True)
for row in _RECOVERY_DATA:
    rc = st.columns([1.5, 2.5, 1.5, 2])
    rc_color = _RECOVERY_COLORS.get(row["Recovery"], COLORS["iron"])
    rc[0].markdown(f"<span style='font-size:0.8rem;color:{COLORS['text_primary']};'>{row['Window']}</span>", unsafe_allow_html=True)
    rc[1].markdown(f"<span style='font-size:0.8rem;color:{COLORS['text_primary']};'>{row['Channel']}</span>", unsafe_allow_html=True)
    rc[2].markdown(f"<span style='font-size:0.8rem;font-weight:600;color:{rc_color};'>{row['Recovery']}</span>", unsafe_allow_html=True)
    rc[3].markdown(f"<span style='font-size:0.78rem;color:{COLORS['text_secondary']};'>{row['Manager']}</span>", unsafe_allow_html=True)
card_container_end()

render_chat_drawer(page_key="acq_funnel")
