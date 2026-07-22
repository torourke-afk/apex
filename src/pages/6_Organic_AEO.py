"""
Organic AEO — AI Engine Optimization: LLM visibility, citations, and answer presence
Signal Deck design system
"""

import streamlit as st

from src.components.filter_bar import get_global_filters
from src.components.page_chrome import page_chrome
from src.components.chat_drawer import render_chat_drawer

page_chrome(title="Organic AEO", category="CHANNELS")
filters = get_global_filters()

_mono = "'JetBrains Mono',monospace"
_ff = "'Space Grotesk',system-ui,sans-serif"

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

_KPI_DATA = [
    {"label": "LLM VISIBILITY SCORE", "value": "62.4", "delta": "+4.8 pts", "color": "var(--cyan)"},
    {"label": "AI CITATIONS", "value": "1,847", "delta": "+312 wk/wk", "color": "var(--green)"},
    {"label": "ANSWER PRESENCE", "value": "73%", "delta": "+6.2 pts", "color": "var(--green)"},
    {"label": "CONTENT AUTHORITY", "value": "8.4", "delta": "+0.7", "color": "var(--cyan)"},
]

_CITATIONS = [
    {"query": "best checking account 2026", "engine": "ChatGPT", "position": 1, "type": "Direct Mention"},
    {"query": "high yield savings rates", "engine": "Perplexity", "position": 2, "type": "Cited Source"},
    {"query": "best bank for students", "engine": "Claude", "position": 1, "type": "Direct Mention"},
    {"query": "cd rates comparison", "engine": "ChatGPT", "position": 3, "type": "Indirect Reference"},
    {"query": "mobile banking features", "engine": "Gemini", "position": 4, "type": "Cited Source"},
    {"query": "no fee checking accounts", "engine": "Perplexity", "position": 1, "type": "Direct Mention"},
    {"query": "home equity loan rates", "engine": "ChatGPT", "position": 5, "type": "Indirect Reference"},
    {"query": "bank near me reviews", "engine": "Claude", "position": 2, "type": "Cited Source"},
]

_OPTIMIZATION = [
    {"title": "Product Pages", "score": 84, "status": "Optimized", "color": "var(--green)"},
    {"title": "FAQ Content", "score": 71, "status": "Needs Work", "color": "var(--amber)"},
    {"title": "Rate Pages", "score": 92, "status": "Optimized", "color": "var(--green)"},
    {"title": "Blog Articles", "score": 58, "status": "Below Target", "color": "var(--red)"},
    {"title": "Location Pages", "score": 77, "status": "Needs Work", "color": "var(--amber)"},
    {"title": "Help Center", "score": 89, "status": "Optimized", "color": "var(--green)"},
]

_AI_LANDSCAPE = [
    {"engine": "ChatGPT", "visibility": 68, "trend": "up", "share": "41%"},
    {"engine": "Perplexity", "visibility": 74, "trend": "up", "share": "22%"},
    {"engine": "Claude", "visibility": 61, "trend": "up", "share": "18%"},
    {"engine": "Gemini", "visibility": 52, "trend": "down", "share": "14%"},
    {"engine": "Copilot", "visibility": 44, "trend": "flat", "share": "5%"},
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
# LLM Citation Tracker
# ---------------------------------------------------------------------------

cite_rows = ""
for c in _CITATIONS:
    pos_color = "var(--cyan)" if c["position"] <= 2 else "var(--text2)" if c["position"] <= 4 else "var(--text3)"
    type_bg = "rgba(52,225,212,.12)" if c["type"] == "Direct Mention" else "rgba(79,216,155,.12)" if c["type"] == "Cited Source" else "rgba(242,177,76,.12)"
    type_color = "var(--cyan)" if c["type"] == "Direct Mention" else "var(--green)" if c["type"] == "Cited Source" else "var(--amber)"
    cite_rows += f"""
    <div style="display:grid; grid-template-columns:2.2fr 1fr 0.6fr 1.2fr; gap:8px;
      align-items:center; padding:11px 18px; border-bottom:1px solid var(--line);">
      <span style="font-size:13px; font-weight:500; color:var(--text);">{c['query']}</span>
      <span style="font-family:{_mono}; font-size:11px; color:var(--text2);">{c['engine']}</span>
      <span style="font-family:{_mono}; font-size:13px; font-weight:600; color:{pos_color};">#{c['position']}</span>
      <span style="font-family:{_mono}; font-size:10px; padding:3px 8px; border-radius:6px;
        background:{type_bg}; color:{type_color}; text-align:center;">{c['type']}</span>
    </div>"""

st.markdown(f"""
<section style="border-radius:14px; border:1px solid var(--line); background:var(--panel);
  overflow:hidden; margin-bottom:18px; animation:rise .4s ease-out .12s both;">
  <div style="display:flex; align-items:center; justify-content:space-between; padding:15px 18px;
    border-bottom:1px solid var(--line);">
    <div style="display:flex; align-items:center; gap:10px;">
      <div style="width:3px; height:15px; background:var(--cyan); border-radius:3px;"></div>
      <span style="font-size:14px; font-weight:600;">LLM Citation Tracker</span>
    </div>
    <span style="font-family:{_mono}; font-size:9px; letter-spacing:.1em; color:var(--text3);">LAST 7 DAYS</span>
  </div>
  <div style="display:grid; grid-template-columns:2.2fr 1fr 0.6fr 1.2fr; gap:8px; padding:9px 18px;
    border-bottom:1px solid var(--line); font-family:{_mono}; font-size:9px;
    letter-spacing:.1em; color:var(--text3);">
    <span>QUERY</span><span>ENGINE</span><span>POSITION</span><span>CITATION TYPE</span>
  </div>
  {cite_rows}
</section>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Content Optimization Grid
# ---------------------------------------------------------------------------

opt_cards = ""
for i, o in enumerate(_OPTIMIZATION):
    delay = f"{0.04 * (i + 1):.2f}"
    ring_r = 22
    ring_c = 2 * 3.14159 * ring_r
    ring_offset = ring_c * (1 - o["score"] / 100)
    opt_cards += f"""
    <div style="display:flex; flex-direction:column; align-items:center; padding:18px;
      border-radius:14px; border:1px solid var(--line); background:var(--panel);
      animation:rise .4s ease-out {delay}s both;">
      <svg width="54" height="54" viewBox="0 0 54 54">
        <circle cx="27" cy="27" r="{ring_r}" fill="none" stroke="var(--line)" stroke-width="4"/>
        <circle cx="27" cy="27" r="{ring_r}" fill="none" stroke="{o['color']}" stroke-width="4"
                stroke-linecap="round" stroke-dasharray="{ring_c:.1f}" stroke-dashoffset="{ring_offset:.1f}"
                transform="rotate(-90 27 27)"/>
        <text x="27" y="31" text-anchor="middle" font-family="{_mono}" font-size="12"
              font-weight="600" fill="var(--text)">{o['score']}</text>
      </svg>
      <span style="font-size:12px; font-weight:600; color:var(--text); margin-top:10px;">{o['title']}</span>
      <span style="font-family:{_mono}; font-size:9px; letter-spacing:.06em; color:{o['color']}; margin-top:4px;">{o['status'].upper()}</span>
    </div>"""

st.markdown(f"""
<section style="border-radius:14px; border:1px solid var(--line); background:var(--panel);
  overflow:hidden; margin-bottom:18px; animation:rise .4s ease-out .18s both;">
  <div style="display:flex; align-items:center; justify-content:space-between; padding:15px 18px;
    border-bottom:1px solid var(--line);">
    <div style="display:flex; align-items:center; gap:10px;">
      <div style="width:3px; height:15px; background:var(--cyan); border-radius:3px;"></div>
      <span style="font-size:14px; font-weight:600;">Content Optimization</span>
    </div>
    <span style="font-family:{_mono}; font-size:9px; letter-spacing:.1em; color:var(--text3);">AEO READINESS</span>
  </div>
  <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:14px; padding:18px;">
    {opt_cards}
  </div>
</section>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# AI Search Landscape
# ---------------------------------------------------------------------------

landscape_rows = ""
for ai in _AI_LANDSCAPE:
    trend_icon = "↑" if ai["trend"] == "up" else "↓" if ai["trend"] == "down" else "→"
    trend_color = "var(--green)" if ai["trend"] == "up" else "var(--red)" if ai["trend"] == "down" else "var(--text3)"
    bar_w = ai["visibility"]
    landscape_rows += f"""
    <div style="display:grid; grid-template-columns:1.2fr 2.5fr 0.6fr 0.8fr; gap:12px;
      align-items:center; padding:11px 18px; border-bottom:1px solid var(--line);">
      <span style="font-size:13px; font-weight:500; color:var(--text);">{ai['engine']}</span>
      <div style="display:flex; align-items:center; gap:8px;">
        <div style="flex:1; height:6px; border-radius:5px; background:var(--line); overflow:hidden;">
          <div style="width:{bar_w}%; height:100%; border-radius:5px; background:var(--cyan);
            transition:width .6s ease;"></div>
        </div>
        <span style="font-family:{_mono}; font-size:12px; font-weight:600; min-width:28px; text-align:right;">{ai['visibility']}</span>
      </div>
      <span style="font-family:{_mono}; font-size:12px; font-weight:600; color:{trend_color}; text-align:center;">{trend_icon}</span>
      <span style="font-family:{_mono}; font-size:11px; color:var(--text2); text-align:right;">{ai['share']}</span>
    </div>"""

st.markdown(f"""
<section style="border-radius:14px; border:1px solid var(--line); background:var(--panel);
  overflow:hidden; animation:rise .4s ease-out .24s both;">
  <div style="display:flex; align-items:center; justify-content:space-between; padding:15px 18px;
    border-bottom:1px solid var(--line);">
    <div style="display:flex; align-items:center; gap:10px;">
      <div style="width:3px; height:15px; background:var(--cyan); border-radius:3px;"></div>
      <span style="font-size:14px; font-weight:600;">AI Search Landscape</span>
    </div>
    <span style="font-family:{_mono}; font-size:9px; letter-spacing:.1em; color:var(--text3);">VISIBILITY BY ENGINE</span>
  </div>
  <div style="display:grid; grid-template-columns:1.2fr 2.5fr 0.6fr 0.8fr; gap:12px; padding:9px 18px;
    border-bottom:1px solid var(--line); font-family:{_mono}; font-size:9px;
    letter-spacing:.1em; color:var(--text3);">
    <span>ENGINE</span><span>VISIBILITY SCORE</span><span>TREND</span><span style="text-align:right;">TRAFFIC SHARE</span>
  </div>
  {landscape_rows}
</section>
""", unsafe_allow_html=True)

render_chat_drawer(page_key="aeo")
