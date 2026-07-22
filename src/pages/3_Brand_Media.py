"""
Brand Media -- Signal Deck spec
Brand awareness channels: channel performance table (rolling 4wk), saturation curves, efficiency frontier.
"""
import streamlit as st

from src.components.filter_bar import get_global_filters
from src.components.page_chrome import page_chrome
from src.components.chat_drawer import render_chat_drawer

# ---------------------------------------------------------------------------
# Seed / fallback data
# ---------------------------------------------------------------------------

_CHANNELS = [
    {
        "name": "Brand TV",
        "dot": "var(--cyan)",
        "spend": "$1.82M",
        "cpihh": "$348",
        "cvr": "2.1%",
        "roas": "3.2x",
        "spark": "0,18 10,16 20,17 32,12 42,10 54,8 64,6",
    },
    {
        "name": "Brand Display",
        "dot": "var(--amber)",
        "spend": "$640K",
        "cpihh": "$412",
        "cvr": "1.4%",
        "roas": "2.6x",
        "spark": "0,8 10,10 20,12 32,14 42,11 54,15 64,18",
    },
    {
        "name": "Brand Social",
        "dot": "var(--green)",
        "spend": "$520K",
        "cpihh": "$289",
        "cvr": "2.8%",
        "roas": "3.9x",
        "spark": "0,18 10,15 20,14 32,10 42,11 54,7 64,4",
    },
    {
        "name": "Sponsorships",
        "dot": "var(--text3)",
        "spend": "$310K",
        "cpihh": "$510",
        "cvr": "0.9%",
        "roas": "1.8x",
        "spark": "0,12 10,12 20,11 32,13 42,14 54,12 64,11",
    },
]

# Saturation curve data points (Hill function curves)
_SAT_CURVES = [
    {"label": "Brand TV", "color": "var(--cyan)", "points": "0,180 40,140 80,100 120,70 160,50 200,38 240,30 280,25"},
    {"label": "Brand Social", "color": "var(--green)", "points": "0,180 40,150 80,120 120,95 160,75 200,60 240,50 280,44"},
    {"label": "Sponsorships", "color": "var(--amber)", "points": "0,180 40,160 80,140 120,125 160,110 200,100 240,92 280,86"},
]
_SAT_DOTS = [
    {"cx": 160, "cy": 50, "color": "var(--cyan)"},
    {"cx": 80, "cy": 120, "color": "var(--green)"},
    {"cx": 120, "cy": 125, "color": "var(--amber)"},
]

# Efficiency frontier bubble data
_FRONTIER_BUBBLES = [
    {"label": "SEM", "x": 42, "y": 145, "r": 18, "color": "var(--cyan)"},
    {"label": "BRAND", "x": 28, "y": 100, "r": 24, "color": "var(--amber)"},
    {"label": "SOCIAL", "x": 18, "y": 155, "r": 14, "color": "var(--green)"},
    {"label": "MAIL", "x": 12, "y": 70, "r": 10, "color": "var(--text3)"},
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_mono = "'JetBrains Mono',monospace"
_ff = "'Space Grotesk',system-ui,sans-serif"


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

page_chrome(title="Brand Media", category="CHANNELS")
filters = get_global_filters()


# -- Channel Performance Table ------------------------------------------------

_channel_rows = ""
for i, ch in enumerate(_CHANNELS):
    delay = f"{0.04 * (i + 1):.2f}"
    _channel_rows += f"""
    <div style="display:grid; grid-template-columns:1.3fr 90px 96px 88px 88px 90px;
      gap:8px; align-items:center; padding:11px 18px; border-bottom:1px solid var(--line);
      animation:rise .4s ease-out {delay}s both;">
      <div style="display:flex; align-items:center; gap:9px;">
        <div style="width:8px; height:8px; border-radius:2px; background:{ch['dot']}; flex:none;"></div>
        <span style="font-size:13px; font-weight:500; color:var(--text);">{ch['name']}</span>
      </div>
      <span style="font-family:{_mono}; font-size:12px; color:var(--text); text-align:right;">{ch['spend']}</span>
      <span style="font-family:{_mono}; font-size:12px; color:var(--text); text-align:right;">{ch['cpihh']}</span>
      <span style="font-family:{_mono}; font-size:12px; color:var(--text); text-align:right;">{ch['cvr']}</span>
      <span style="font-family:{_mono}; font-size:12px; color:var(--text); text-align:right;">{ch['roas']}</span>
      <div style="display:flex; justify-content:flex-end;">
        <svg width="64" height="22" viewBox="0 0 64 22" fill="none">
          <polyline points="{ch['spark']}" stroke="{ch['dot']}" stroke-width="1.6"
                    stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
    </div>"""

st.markdown(f"""
<section style="border-radius:14px; border:1px solid var(--line); background:var(--panel);
  overflow:hidden; margin-bottom:16px; animation:rise .4s ease-out both;">
  <!-- Header -->
  <div style="display:flex; align-items:center; justify-content:space-between; padding:15px 18px;
    border-bottom:1px solid var(--line);">
    <div style="display:flex; align-items:center; gap:10px;">
      <div style="width:3px; height:15px; background:var(--cyan); border-radius:3px;"></div>
      <span style="font-size:14px; font-weight:600; color:var(--text);">Channel Performance</span>
    </div>
    <span style="font-family:{_mono}; font-size:9.5px; letter-spacing:.1em; color:var(--text3);">ROLLING 4 WEEKS</span>
  </div>
  <!-- Column headers -->
  <div style="display:grid; grid-template-columns:1.3fr 90px 96px 88px 88px 90px;
    gap:8px; padding:9px 18px; border-bottom:1px solid var(--line);
    font-family:{_mono}; font-size:9px; letter-spacing:.1em; color:var(--text3);">
    <span>CHANNEL</span>
    <span style="text-align:right;">SPEND</span>
    <span style="text-align:right;">CPIHH</span>
    <span style="text-align:right;">CVR</span>
    <span style="text-align:right;">ROAS</span>
    <span style="text-align:right;">TREND</span>
  </div>
  {_channel_rows}
</section>
""", unsafe_allow_html=True)


# -- Saturation Curves + Efficiency Frontier (side by side) -------------------

# Build saturation curves SVG
_sat_paths = ""
for curve in _SAT_CURVES:
    _sat_paths += f"""
      <polyline points="{curve['points']}" stroke="{curve['color']}" stroke-width="2"
                stroke-linecap="round" stroke-linejoin="round" fill="none"/>"""

_sat_dots_svg = ""
for dot in _SAT_DOTS:
    _sat_dots_svg += f"""
      <circle cx="{dot['cx']}" cy="{dot['cy']}" r="5" fill="{dot['color']}"
              stroke="var(--panel)" stroke-width="2"/>"""

_sat_legend = ""
for curve in _SAT_CURVES:
    _sat_legend += f"""
      <div style="display:flex; align-items:center; gap:6px;">
        <div style="width:16px; height:2px; background:{curve['color']}; border-radius:1px;"></div>
        <span style="font-family:{_mono}; font-size:9px; letter-spacing:.06em; color:var(--text2);">{curve['label'].upper()}</span>
      </div>"""

# Build efficiency frontier SVG
_frontier_bubbles_svg = ""
_frontier_labels_svg = ""
for b in _FRONTIER_BUBBLES:
    # Map x (spend share %) and y (ROAS) into SVG coords
    bx = 30 + b["x"] * 4.5  # scale spend share to SVG x
    by = 190 - b["y"]       # invert y for SVG
    _frontier_bubbles_svg += f"""
      <circle cx="{bx}" cy="{by}" r="{b['r']}" fill="{b['color']}" opacity="0.35"
              stroke="{b['color']}" stroke-width="1.5"/>"""
    _frontier_labels_svg += f"""
      <text x="{bx}" y="{by + 4}" text-anchor="middle" font-family="{_mono}" font-size="9"
            font-weight="500" fill="var(--text)" letter-spacing=".06em">{b['label']}</text>"""


st.markdown(f"""
<div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:16px;">

  <!-- Saturation Curves -->
  <section style="border-radius:14px; border:1px solid var(--line); background:var(--panel);
    overflow:hidden; animation:rise .4s ease-out .08s both;">
    <div style="display:flex; align-items:center; justify-content:space-between; padding:15px 18px;
      border-bottom:1px solid var(--line);">
      <div style="display:flex; align-items:center; gap:10px;">
        <div style="width:3px; height:15px; background:var(--cyan); border-radius:3px;"></div>
        <span style="font-size:14px; font-weight:600; color:var(--text);">Saturation Curves</span>
      </div>
      <span style="font-family:{_mono}; font-size:9.5px; letter-spacing:.1em; color:var(--text3);">HILL RESPONSE</span>
    </div>
    <div style="padding:20px 18px 12px;">
      <svg width="100%" viewBox="0 0 300 200" preserveAspectRatio="xMidYMid meet">
        <!-- Axes -->
        <line x1="20" y1="185" x2="290" y2="185" stroke="var(--line)" stroke-width="1"/>
        <line x1="20" y1="10" x2="20" y2="185" stroke="var(--line)" stroke-width="1"/>
        <!-- Axis labels -->
        <text x="155" y="198" text-anchor="middle" font-family="{_mono}" font-size="8"
              fill="var(--text3)" letter-spacing=".08em">SPEND LEVEL</text>
        <text x="8" y="100" text-anchor="middle" font-family="{_mono}" font-size="8"
              fill="var(--text3)" letter-spacing=".08em" transform="rotate(-90 8 100)">RESPONSE</text>
        <!-- Grid lines -->
        <line x1="20" y1="60" x2="290" y2="60" stroke="var(--line)" stroke-width="0.5" stroke-dasharray="4"/>
        <line x1="20" y1="120" x2="290" y2="120" stroke="var(--line)" stroke-width="0.5" stroke-dasharray="4"/>
        <!-- Curves -->
        {_sat_paths}
        <!-- Current spend dots -->
        {_sat_dots_svg}
      </svg>
      <!-- Legend -->
      <div style="display:flex; gap:16px; justify-content:center; margin-top:8px;">
        {_sat_legend}
      </div>
    </div>
  </section>

  <!-- Efficiency Frontier -->
  <section style="border-radius:14px; border:1px solid var(--line); background:var(--panel);
    overflow:hidden; animation:rise .4s ease-out .12s both;">
    <div style="display:flex; align-items:center; justify-content:space-between; padding:15px 18px;
      border-bottom:1px solid var(--line);">
      <div style="display:flex; align-items:center; gap:10px;">
        <div style="width:3px; height:15px; background:var(--cyan); border-radius:3px;"></div>
        <span style="font-size:14px; font-weight:600; color:var(--text);">Efficiency Frontier</span>
      </div>
      <span style="font-family:{_mono}; font-size:9.5px; letter-spacing:.1em; color:var(--text3);">ROAS vs SPEND</span>
    </div>
    <div style="padding:20px 18px 12px;">
      <svg width="100%" viewBox="0 0 300 210" preserveAspectRatio="xMidYMid meet">
        <!-- Axes -->
        <line x1="30" y1="190" x2="280" y2="190" stroke="var(--line)" stroke-width="1"/>
        <line x1="30" y1="10" x2="30" y2="190" stroke="var(--line)" stroke-width="1"/>
        <!-- Axis labels -->
        <text x="155" y="207" text-anchor="middle" font-family="{_mono}" font-size="8"
              fill="var(--text3)" letter-spacing=".08em">SPEND SHARE %</text>
        <text x="10" y="100" text-anchor="middle" font-family="{_mono}" font-size="8"
              fill="var(--text3)" letter-spacing=".08em" transform="rotate(-90 10 100)">ROAS</text>
        <!-- Grid -->
        <line x1="30" y1="60" x2="280" y2="60" stroke="var(--line)" stroke-width="0.5" stroke-dasharray="4"/>
        <line x1="30" y1="120" x2="280" y2="120" stroke="var(--line)" stroke-width="0.5" stroke-dasharray="4"/>
        <!-- Portfolio AVG dashed line -->
        <line x1="30" y1="80" x2="280" y2="80" stroke="var(--text3)" stroke-width="1" stroke-dasharray="6 3"/>
        <text x="282" y="78" font-family="{_mono}" font-size="8" fill="var(--text3)">AVG</text>
        <!-- Bubbles -->
        {_frontier_bubbles_svg}
        {_frontier_labels_svg}
      </svg>
      <div style="display:flex; gap:14px; justify-content:center; margin-top:8px;">
        <span style="font-family:{_mono}; font-size:9px; color:var(--text3); letter-spacing:.06em;">
          BUBBLE SIZE = FUNDED VOLUME</span>
        <span style="font-family:{_mono}; font-size:9px; color:var(--text3); letter-spacing:.06em;">
          --- PORTFOLIO AVG</span>
      </div>
    </div>
  </section>

</div>
""", unsafe_allow_html=True)


render_chat_drawer(page_key="brand_media")
