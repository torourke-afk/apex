"""
Brand Awareness Tracker
-----------------------
Signal Deck implementation: MSV-based competitive brand intelligence dashboard.
Pure HTML/CSS via st.markdown — no Plotly, no native Streamlit data components.
"""

import streamlit as st

from src.components.filter_bar import get_global_filters
from src.components.page_chrome import page_chrome
from src.components.chat_drawer import render_chat_drawer

try:
    from src.data.brand_awareness import (
        TrackerConfig, config_to_json, default_fitb_config,
        load_msv_data, load_dma_msv_data, load_share_of_search,
        compute_peer_comparison, recommend_competitors,
        get_available_dmas, PEER_PRESETS, FITB_PRESET, SEMRUSH_API_KEY,
    )
    _HAS_DEPS = True
except ImportError:
    _HAS_DEPS = False

# ---------------------------------------------------------------------------
# Page chrome
# ---------------------------------------------------------------------------

page_chrome(title="Brand Awareness", category="CHANNELS")
filters = get_global_filters()

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
# Sample data
# ---------------------------------------------------------------------------

_KPIS = [
    {"label": "SHARE OF SEARCH", "value": "24.6%", "delta": "↑ 1.2pp QoQ", "color": "var(--green)"},
    {"label": "BRAND RECALL", "value": "68%", "delta": "↑ 3pts vs H1", "color": "var(--green)"},
    {"label": "UNAIDED AWARENESS", "value": "41%", "delta": "↓ 1pt vs target 44%", "color": "var(--amber)"},
    {"label": "NET PROMOTER SCORE", "value": "+38", "delta": "↑ 4pts YoY", "color": "var(--cyan)"},
]

_COMPETITORS = [
    {"brand": "Fifth Third Bank", "share": "24.6%", "delta": "+1.2pp", "sentiment": "Positive", "sent_color": "var(--green)", "sent_bg": "rgba(79,216,155,.14)", "trend": "↑", "trend_color": "var(--green)", "own": True},
    {"brand": "Huntington", "share": "22.1%", "delta": "+0.4pp", "sentiment": "Neutral", "sent_color": "var(--text2)", "sent_bg": "var(--panel2)", "trend": "→", "trend_color": "var(--text2)", "own": False},
    {"brand": "KeyBank", "share": "18.8%", "delta": "-0.8pp", "sentiment": "Mixed", "sent_color": "var(--amber)", "sent_bg": "rgba(242,177,76,.14)", "trend": "↓", "trend_color": "var(--amber)", "own": False},
    {"brand": "PNC", "share": "19.4%", "delta": "+0.2pp", "sentiment": "Positive", "sent_color": "var(--green)", "sent_bg": "rgba(79,216,155,.14)", "trend": "↑", "trend_color": "var(--green)", "own": False},
    {"brand": "U.S. Bank", "share": "15.1%", "delta": "-1.0pp", "sentiment": "Neutral", "sent_color": "var(--text2)", "sent_bg": "var(--panel2)", "trend": "→", "trend_color": "var(--text2)", "own": False},
]

_HEALTH_SCORES = [
    {"label": "TRUST", "score": 76, "fill_color": "var(--cyan)"},
    {"label": "CONSIDERATION", "score": 62, "fill_color": "var(--green)"},
    {"label": "PREFERENCE", "score": 48, "fill_color": "var(--amber)"},
    {"label": "ADVOCACY", "score": 54, "fill_color": "var(--green)"},
]

_MONTHS = ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun"]

# ---------------------------------------------------------------------------
# Font aliases
# ---------------------------------------------------------------------------

_mono = "'JetBrains Mono',monospace"
_ff = "'Space Grotesk',system-ui,sans-serif"

# ---------------------------------------------------------------------------
# 1. KPI Cards
# ---------------------------------------------------------------------------

_kpi_cards = ""
for i, kpi in enumerate(_KPIS):
    delay = f"{0.05 * (i + 1):.2f}"
    _kpi_cards += (
        f'<div style="padding:16px 18px;border-radius:14px;border:1px solid var(--line);'
        f'background:var(--panel);animation:rise .4s ease-out {delay}s both;">'
        f'<div style="font-family:{_mono};font-size:9.5px;letter-spacing:.12em;'
        f'color:var(--text3);text-transform:uppercase;">{kpi["label"]}</div>'
        f'<div style="font-size:26px;font-weight:600;margin-top:6px;font-family:{_mono};'
        f'font-variant-numeric:tabular-nums;color:var(--text);">{kpi["value"]}</div>'
        f'<div style="font-family:{_mono};font-size:10px;margin-top:3px;'
        f'color:{kpi["color"]};">{kpi["delta"]}</div>'
        f'</div>'
    )

st.markdown(
    '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));'
    'gap:14px;margin-bottom:18px;animation:rise .4s ease-out both;">'
    + _kpi_cards
    + '</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 2. Share of Search Trend (SVG line chart)
# ---------------------------------------------------------------------------

_month_labels = ""
for m in _MONTHS:
    _month_labels += (
        f'<span style="font-family:{_mono};font-size:9px;color:var(--text3);">{m}</span>'
    )

st.markdown(
    '<div style="border-radius:14px;border:1px solid var(--line);background:var(--panel);'
    'padding:18px;margin-bottom:18px;animation:rise .4s ease-out .12s both;">'
    # Section header
    '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">'
    '<div style="display:flex;align-items:center;gap:10px;">'
    '<div style="width:3px;height:15px;background:var(--cyan);border-radius:3px;"></div>'
    '<span style="font-size:14px;font-weight:600;color:var(--text);">Share of Search Trend</span>'
    '</div>'
    f'<span style="font-family:{_mono};font-size:9.5px;letter-spacing:.1em;color:var(--text3);">'
    '12-MONTH &middot; BRANDED KEYWORDS</span>'
    '</div>'
    # SVG chart
    '<svg viewBox="0 0 560 200" width="100%" height="200" style="display:block;margin-top:10px;">'
    '<line x1="0" y1="198" x2="560" y2="198" stroke="var(--line2)" stroke-width="1"/>'
    '<line x1="0" y1="132" x2="560" y2="132" stroke="var(--line)" stroke-width="1" stroke-dasharray="4 4"/>'
    '<line x1="0" y1="66" x2="560" y2="66" stroke="var(--line)" stroke-width="1" stroke-dasharray="4 4"/>'
    '<defs><linearGradient id="sosfill" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="var(--cyan)" stop-opacity="0.22"/>'
    '<stop offset="1" stop-color="var(--cyan)" stop-opacity="0"/>'
    '</linearGradient></defs>'
    '<path d="M0,152 47,148 94,140 141,138 188,134 235,128 282,120 329,112 376,106 423,98 470,90 517,84 560,78 L560,198 L0,198 Z" fill="url(#sosfill)"/>'
    '<polyline points="0,152 47,148 94,140 141,138 188,134 235,128 282,120 329,112 376,106 423,98 470,90 517,84 560,78" '
    'fill="none" stroke="var(--cyan)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>'
    '</svg>'
    # X-axis labels
    '<div style="display:flex;justify-content:space-between;padding:6px 0 0 0;">'
    + _month_labels +
    '</div>'
    # Legend
    '<div style="display:flex;align-items:center;gap:14px;margin-top:8px;">'
    f'<span style="display:flex;align-items:center;gap:6px;font-family:{_mono};font-size:9px;'
    'letter-spacing:.06em;color:var(--text3);">'
    '<span style="width:14px;height:2px;background:var(--cyan);display:inline-block;"></span>'
    'FIFTH THIRD SHARE</span>'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 3. Brand vs Competitors table
# ---------------------------------------------------------------------------

_comp_rows = ""
for i, c in enumerate(_COMPETITORS):
    left_border = "border-left:2px solid var(--cyan);" if c["own"] else ""
    brand_weight = "font-weight:600;" if c["own"] else ""
    brand_text_color = "color:var(--cyan);" if c["own"] else "color:var(--text);"
    delay = f"{0.04 * (i + 1):.2f}"

    _comp_rows += (
        f'<div style="display:grid;grid-template-columns:1.4fr 1fr 80px 90px 80px;gap:8px;'
        f'padding:12px 18px;border-bottom:1px solid var(--line);{left_border}'
        f'animation:rise .4s ease-out {delay}s both;">'
        # Brand name
        f'<div style="font-family:{_ff};font-size:13px;{brand_weight}'
        f'{brand_text_color}">{c["brand"]}</div>'
        # Share
        f'<div style="font-family:{_mono};font-size:13px;font-variant-numeric:tabular-nums;'
        f'color:var(--text);">{c["share"]}</div>'
        # Delta QoQ
        f'<div style="font-family:{_mono};font-size:12px;font-variant-numeric:tabular-nums;'
        f'color:var(--text2);">{c["delta"]}</div>'
        # Sentiment badge
        f'<div><span style="font-family:{_mono};font-size:9px;letter-spacing:.06em;'
        f'padding:3px 8px;border-radius:6px;color:{c["sent_color"]};'
        f'background:{c["sent_bg"]};">{c["sentiment"]}</span></div>'
        # Trend arrow
        f'<div style="font-size:14px;color:{c["trend_color"]};text-align:center;">{c["trend"]}</div>'
        f'</div>'
    )

st.markdown(
    '<div style="border-radius:14px;border:1px solid var(--line);background:var(--panel);'
    'padding:0;margin-bottom:18px;overflow:hidden;animation:rise .4s ease-out .16s both;">'
    # Section header
    '<div style="display:flex;align-items:center;justify-content:space-between;padding:18px 18px 12px 18px;">'
    '<div style="display:flex;align-items:center;gap:10px;">'
    '<div style="width:3px;height:15px;background:var(--cyan);border-radius:3px;"></div>'
    '<span style="font-size:14px;font-weight:600;color:var(--text);">Brand vs Competitors</span>'
    '</div>'
    f'<span style="font-family:{_mono};font-size:9.5px;letter-spacing:.1em;color:var(--text3);">'
    'LATEST MONTH &middot; MSV RANKED</span>'
    '</div>'
    # Column headers
    f'<div style="display:grid;grid-template-columns:1.4fr 1fr 80px 90px 80px;gap:8px;'
    f'padding:9px 18px;border-bottom:1px solid var(--line);'
    f'font-family:{_mono};font-size:9px;letter-spacing:.1em;color:var(--text3);">'
    '<div>BRAND</div><div>SHARE</div><div>&Delta; QoQ</div><div>SENTIMENT</div><div style="text-align:center;">TREND</div>'
    '</div>'
    # Data rows
    + _comp_rows +
    '</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 4. Brand Health Index
# ---------------------------------------------------------------------------

_health_cards = ""
for i, h in enumerate(_HEALTH_SCORES):
    delay = f"{0.05 * (i + 1):.2f}"
    fill_width = h["score"]
    _health_cards += (
        f'<div style="padding:16px;border-radius:12px;border:1px solid var(--line);'
        f'background:var(--panel2);text-align:center;animation:rise .4s ease-out {delay}s both;">'
        # Score
        f'<div style="font-size:28px;font-weight:600;font-family:{_mono};'
        f'font-variant-numeric:tabular-nums;color:var(--text);">{h["score"]}</div>'
        # Label
        f'<div style="font-family:{_mono};font-size:9px;letter-spacing:.1em;'
        f'color:var(--text3);margin-top:6px;">{h["label"]}</div>'
        # Bar
        f'<div style="height:4px;border-radius:4px;background:var(--line);margin-top:8px;overflow:hidden;">'
        f'<div style="width:{fill_width}%;height:100%;border-radius:4px;background:{h["fill_color"]};"></div>'
        f'</div>'
        f'</div>'
    )

st.markdown(
    '<div style="border-radius:14px;border:1px solid var(--line);background:var(--panel);'
    'padding:18px;margin-bottom:18px;animation:rise .4s ease-out .2s both;">'
    # Section header
    '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">'
    '<div style="display:flex;align-items:center;gap:10px;">'
    '<div style="width:3px;height:15px;background:var(--cyan);border-radius:3px;"></div>'
    '<span style="font-size:14px;font-weight:600;color:var(--text);">Brand Health Index</span>'
    '</div>'
    f'<span style="font-family:{_mono};font-size:9.5px;letter-spacing:.1em;color:var(--text3);">'
    'COMPOSITE TRACKER &middot; Q2 2026</span>'
    '</div>'
    # Grid of mini score cards
    '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;">'
    + _health_cards +
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Chat drawer
# ---------------------------------------------------------------------------

render_chat_drawer(page_key="brand_awareness")
