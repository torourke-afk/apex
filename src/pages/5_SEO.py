"""
SEO — Organic search rankings, traffic, and keyword performance
Signal Deck design system
"""

import streamlit as st

from src.components.filter_bar import get_global_filters
from src.components.page_chrome import page_chrome
from src.components.chat_drawer import render_chat_drawer

page_chrome(title="SEO", category="CHANNELS")
filters = get_global_filters()

_mono = "'JetBrains Mono',monospace"
_ff = "'Space Grotesk',system-ui,sans-serif"

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

_KPI_DATA = [
    {"label": "ORGANIC SESSIONS", "value": "1.42M", "delta": "+8.3%", "color": "var(--green)"},
    {"label": "KEYWORD RANKINGS", "value": "312", "delta": "+24 new", "color": "var(--green)"},
    {"label": "DOMAIN AUTHORITY", "value": "68", "delta": "+2 pts", "color": "var(--green)"},
    {"label": "CLICK-THROUGH RATE", "value": "3.8%", "delta": "+0.4 pts", "color": "var(--cyan)"},
]

_KEYWORDS = [
    {"kw": "best checking account", "pos": 4, "vol": "18,100", "ctr": "8.2%", "trend": "up"},
    {"kw": "high yield savings", "pos": 8, "vol": "33,100", "ctr": "5.1%", "trend": "up"},
    {"kw": "free checking near me", "pos": 6, "vol": "12,400", "ctr": "6.8%", "trend": "up"},
    {"kw": "cd rates today", "pos": 12, "vol": "49,500", "ctr": "3.2%", "trend": "down"},
    {"kw": "student checking account", "pos": 3, "vol": "8,100", "ctr": "9.4%", "trend": "up"},
    {"kw": "money market rates", "pos": 15, "vol": "27,100", "ctr": "2.8%", "trend": "down"},
    {"kw": "bank near me", "pos": 7, "vol": "90,500", "ctr": "5.6%", "trend": "up"},
    {"kw": "mobile banking app", "pos": 11, "vol": "14,800", "ctr": "3.9%", "trend": "down"},
]

_RANKING_DIST = [
    {"range": "1-3", "count": 42, "pct": 14},
    {"range": "4-10", "count": 118, "pct": 38},
    {"range": "11-20", "count": 89, "pct": 29},
    {"range": "21-50", "count": 48, "pct": 15},
    {"range": "51+", "count": 15, "pct": 5},
]

_TECH_HEALTH = [
    {"label": "Core Web Vitals", "pct": 87, "color": "var(--green)"},
    {"label": "Mobile Usability", "pct": 94, "color": "var(--cyan)"},
    {"label": "Crawlability", "pct": 91, "color": "var(--green)"},
    {"label": "Schema Markup", "pct": 72, "color": "var(--amber)"},
    {"label": "Page Speed (Avg)", "pct": 81, "color": "var(--green)"},
]

# ---------------------------------------------------------------------------
# KPI Strip
# ---------------------------------------------------------------------------

kpi_cards = ""
for i, k in enumerate(_KPI_DATA):
    delay = f"{0.04 * (i + 1):.2f}"
    kpi_cards += f"""
    <div style="display:flex; flex-direction:column; padding:18px; border-radius:14px;
      border:1px solid var(--line); background:var(--panel);
      animation:rise .4s ease-out {delay}s both;">
      <span style="font-family:{_mono}; font-size:9px; letter-spacing:.1em; color:var(--text3);">{k['label']}</span>
      <span style="font-family:{_ff}; font-size:28px; font-weight:600; letter-spacing:-.02em; margin-top:8px;">{k['value']}</span>
      <span style="font-family:{_mono}; font-size:11px; font-weight:500; color:{k['color']}; margin-top:4px;">{k['delta']}</span>
    </div>"""

st.markdown(f"""
<style>
@keyframes rise {{
  from {{ opacity:0; transform:translateY(12px); }}
  to   {{ opacity:1; transform:translateY(0); }}
}}
</style>
<div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:14px; margin-bottom:18px;">
  {kpi_cards}
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Ranking Distribution (SVG bar chart)
# ---------------------------------------------------------------------------

max_pct = max(r["pct"] for r in _RANKING_DIST)
bars_svg = ""
for i, r in enumerate(_RANKING_DIST):
    bar_h = int(r["pct"] / max_pct * 130)
    x = 40 + i * 120
    y = 170 - bar_h
    opacity = 1.0 if i < 2 else 0.6 if i < 4 else 0.35
    bars_svg += f"""
    <rect x="{x}" y="{y}" width="80" height="{bar_h}" rx="6" fill="var(--cyan)" opacity="{opacity}">
      <animate attributeName="height" from="0" to="{bar_h}" dur="0.5s" begin="{0.08*i}s" fill="freeze"/>
      <animate attributeName="y" from="170" to="{y}" dur="0.5s" begin="{0.08*i}s" fill="freeze"/>
    </rect>
    <text x="{x + 40}" y="{y - 8}" text-anchor="middle" font-family="{_mono}" font-size="11" font-weight="600" fill="var(--text)">{r['count']}</text>
    <text x="{x + 40}" y="{y - 22}" text-anchor="middle" font-family="{_mono}" font-size="9" fill="var(--text3)">{r['pct']}%</text>
    <text x="{x + 40}" y="192" text-anchor="middle" font-family="{_mono}" font-size="10" fill="var(--text3)">{r['range']}</text>"""

st.markdown(f"""
<section style="border-radius:14px; border:1px solid var(--line); background:var(--panel);
  overflow:hidden; margin-bottom:18px; animation:rise .4s ease-out .12s both;">
  <div style="display:flex; align-items:center; justify-content:space-between; padding:15px 18px;
    border-bottom:1px solid var(--line);">
    <div style="display:flex; align-items:center; gap:10px;">
      <div style="width:3px; height:15px; background:var(--cyan); border-radius:3px;"></div>
      <span style="font-size:14px; font-weight:600;">Ranking Distribution</span>
    </div>
    <span style="font-family:{_mono}; font-size:9px; letter-spacing:.1em; color:var(--text3);">TRACKED KEYWORDS</span>
  </div>
  <div style="padding:20px 12px 10px;">
    <svg viewBox="0 0 640 210" width="100%" style="display:block;">
      {bars_svg}
    </svg>
  </div>
</section>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Top Keywords Table
# ---------------------------------------------------------------------------

kw_rows = ""
for kw in _KEYWORDS:
    trend_arrow = "↑" if kw["trend"] == "up" else "↓"
    trend_color = "var(--green)" if kw["trend"] == "up" else "var(--red)"
    kw_rows += f"""
    <div style="display:grid; grid-template-columns:2fr 0.7fr 1fr 0.8fr 0.6fr; gap:8px;
      align-items:center; padding:11px 18px; border-bottom:1px solid var(--line);">
      <span style="font-size:13px; font-weight:500; color:var(--text);">{kw['kw']}</span>
      <span style="font-family:{_mono}; font-size:13px; font-weight:600; color:var(--cyan);">{kw['pos']}</span>
      <span style="font-family:{_mono}; font-size:12px; color:var(--text2);">{kw['vol']}</span>
      <span style="font-family:{_mono}; font-size:12px; color:var(--text2);">{kw['ctr']}</span>
      <span style="font-family:{_mono}; font-size:12px; font-weight:600; color:{trend_color};">{trend_arrow}</span>
    </div>"""

st.markdown(f"""
<section style="border-radius:14px; border:1px solid var(--line); background:var(--panel);
  overflow:hidden; margin-bottom:18px; animation:rise .4s ease-out .18s both;">
  <div style="display:flex; align-items:center; justify-content:space-between; padding:15px 18px;
    border-bottom:1px solid var(--line);">
    <div style="display:flex; align-items:center; gap:10px;">
      <div style="width:3px; height:15px; background:var(--cyan); border-radius:3px;"></div>
      <span style="font-size:14px; font-weight:600;">Top Keywords</span>
    </div>
    <span style="font-family:{_mono}; font-size:9px; letter-spacing:.1em; color:var(--text3);">SEARCH CONSOLE</span>
  </div>
  <div style="display:grid; grid-template-columns:2fr 0.7fr 1fr 0.8fr 0.6fr; gap:8px; padding:9px 18px;
    border-bottom:1px solid var(--line); font-family:{_mono}; font-size:9px;
    letter-spacing:.1em; color:var(--text3);">
    <span>KEYWORD</span><span>POSITION</span><span>VOLUME</span><span>CTR</span><span>TREND</span>
  </div>
  {kw_rows}
</section>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Technical Health
# ---------------------------------------------------------------------------

health_bars = ""
for i, h in enumerate(_TECH_HEALTH):
    delay = f"{0.04 * (i + 1):.2f}"
    health_bars += f"""
    <div style="display:flex; align-items:center; gap:12px; animation:rise .4s ease-out {delay}s both;">
      <span style="flex:none; width:110px; font-family:{_mono}; font-size:10px; letter-spacing:.06em; color:var(--text2);">{h['label']}</span>
      <div style="flex:1; height:6px; border-radius:5px; background:var(--line); overflow:hidden;">
        <div style="width:{h['pct']}%; height:100%; border-radius:5px; background:{h['color']};
          transition:width .6s ease;"></div>
      </div>
      <span style="font-family:{_mono}; font-size:12px; font-weight:600; color:var(--text); min-width:32px; text-align:right;">{h['pct']}</span>
    </div>"""

st.markdown(f"""
<section style="border-radius:14px; border:1px solid var(--line); background:var(--panel);
  overflow:hidden; animation:rise .4s ease-out .24s both;">
  <div style="display:flex; align-items:center; justify-content:space-between; padding:15px 18px;
    border-bottom:1px solid var(--line);">
    <div style="display:flex; align-items:center; gap:10px;">
      <div style="width:3px; height:15px; background:var(--cyan); border-radius:3px;"></div>
      <span style="font-size:14px; font-weight:600;">Technical Health</span>
    </div>
    <span style="font-family:{_mono}; font-size:9px; letter-spacing:.1em; color:var(--text3);">SITE AUDIT</span>
  </div>
  <div style="display:flex; flex-direction:column; gap:14px; padding:18px;">
    {health_bars}
  </div>
</section>
""", unsafe_allow_html=True)

render_chat_drawer(page_key="seo")
