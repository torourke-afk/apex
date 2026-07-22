"""
Acquisition Funnel — Sankey diagram and conversion metrics
Signal Deck design system
"""

import streamlit as st

from src.components.filter_bar import get_global_filters
from src.components.page_chrome import page_chrome
from src.components.chat_drawer import render_chat_drawer

page_chrome(title="Acquisition Funnel", category="FUNNEL")
filters = get_global_filters()

_mono = "'JetBrains Mono',monospace"
_ff = "'Space Grotesk',system-ui,sans-serif"

# ---------------------------------------------------------------------------
# Sankey Diagram
# ---------------------------------------------------------------------------

st.markdown(f"""
<style>
@keyframes rise {{
  from {{ opacity:0; transform:translateY(12px); }}
  to   {{ opacity:1; transform:translateY(0); }}
}}
</style>
<section style="border-radius:14px; border:1px solid var(--line); background:var(--panel);
  overflow:hidden; margin-bottom:18px; animation:rise .4s ease-out both;">
  <div style="display:flex; align-items:center; justify-content:space-between; padding:15px 18px;
    border-bottom:1px solid var(--line);">
    <div style="display:flex; align-items:center; gap:10px;">
      <div style="width:3px; height:15px; background:var(--cyan); border-radius:3px;"></div>
      <span style="font-size:14px; font-weight:600;">Acquisition Funnel</span>
    </div>
    <span style="font-family:{_mono}; font-size:9px; letter-spacing:.1em; color:var(--text3);">CHANNEL SOURCE &rarr; FUNDED</span>
  </div>
  <div style="padding:24px 18px 16px;">
    <svg viewBox="0 0 980 340" width="100%" style="display:block;">
      <!-- ribbons channel->visits -->
      <path d="M24,20 C150,20 150,20 266,20 L266,90 C150,90 150,90 24,90 Z" fill="var(--cyan)" opacity="0.22"/>
      <path d="M24,90 C150,90 150,90 266,90 L266,145 C150,145 150,145 24,145 Z" fill="var(--amber)" opacity="0.22"/>
      <path d="M24,145 C150,145 150,145 266,145 L266,225 C150,225 150,225 24,225 Z" fill="var(--green)" opacity="0.22"/>
      <path d="M24,225 C150,225 150,225 266,225 L266,260 C150,260 150,260 24,260 Z" fill="#7C8BFF" opacity="0.22"/>
      <path d="M24,260 C150,260 150,260 266,260 L266,305 C150,305 150,305 24,305 Z" fill="var(--text3)" opacity="0.28"/>
      <!-- visits->leads -->
      <path d="M266,20 C373,20 373,70 480,70 L480,280 C373,280 373,305 266,305 Z" fill="var(--cyan)" opacity="0.16"/>
      <!-- leads->apps -->
      <path d="M496,70 C598,70 598,110 700,110 L700,230 C598,230 598,280 496,280 Z" fill="var(--cyan)" opacity="0.2"/>
      <!-- apps->funded -->
      <path d="M716,110 C823,110 823,150 930,150 L930,210 C823,210 823,230 716,230 Z" fill="var(--cyan)" opacity="0.32"/>
      <!-- nodes -->
      <rect x="10" y="20" width="14" height="70" rx="3" fill="var(--cyan)"/>
      <rect x="10" y="90" width="14" height="55" rx="3" fill="var(--amber)"/>
      <rect x="10" y="145" width="14" height="80" rx="3" fill="var(--green)"/>
      <rect x="10" y="225" width="14" height="35" rx="3" fill="#7C8BFF"/>
      <rect x="10" y="260" width="14" height="45" rx="3" fill="var(--text3)"/>
      <rect x="250" y="20" width="16" height="285" rx="3" fill="var(--text2)"/>
      <rect x="480" y="70" width="16" height="210" rx="3" fill="var(--cyan)"/>
      <rect x="700" y="110" width="16" height="120" rx="3" fill="var(--cyan)"/>
      <rect x="930" y="150" width="16" height="60" rx="3" fill="var(--cyan)"/>
      <!-- labels -->
      <text x="32" y="58" font-family="'JetBrains Mono',monospace" font-size="11" fill="var(--text)">SEM · 41%</text>
      <text x="32" y="121" font-family="'JetBrains Mono',monospace" font-size="11" fill="var(--text)">Social · 22%</text>
      <text x="32" y="188" font-family="'JetBrains Mono',monospace" font-size="11" fill="var(--text)">Brand · 24%</text>
      <text x="32" y="245" font-family="'JetBrains Mono',monospace" font-size="10" fill="var(--text2)">Email</text>
      <text x="32" y="288" font-family="'JetBrains Mono',monospace" font-size="10" fill="var(--text2)">Direct</text>
      <text x="258" y="328" text-anchor="middle" font-family="'JetBrains Mono',monospace" font-size="10" fill="var(--text3)">VISITS</text>
      <text x="258" y="14" text-anchor="middle" font-family="'Space Grotesk'" font-size="13" font-weight="600" fill="var(--text)">1.42M</text>
      <text x="488" y="328" text-anchor="middle" font-family="'JetBrains Mono',monospace" font-size="10" fill="var(--text3)">LEADS</text>
      <text x="488" y="62" text-anchor="middle" font-family="'Space Grotesk'" font-size="13" font-weight="600" fill="var(--text)">91.0K</text>
      <text x="708" y="328" text-anchor="middle" font-family="'JetBrains Mono',monospace" font-size="10" fill="var(--text3)">APPLICATIONS</text>
      <text x="708" y="102" text-anchor="middle" font-family="'Space Grotesk'" font-size="13" font-weight="600" fill="var(--text)">32.0K</text>
      <text x="938" y="328" text-anchor="middle" font-family="'JetBrains Mono',monospace" font-size="10" fill="var(--cyan)">FUNDED</text>
      <text x="938" y="142" text-anchor="middle" font-family="'Space Grotesk'" font-size="13" font-weight="700" fill="var(--cyan)">18.4K</text>
    </svg>
  </div>
</section>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Conversion Rate Cards
# ---------------------------------------------------------------------------

_CVR_DATA = [
    {"label": "VISIT → LEAD", "value": "6.4%", "delta": "+0.3 pts", "color": "var(--green)", "bench": "5.8% bench"},
    {"label": "LEAD → APP", "value": "35.2%", "delta": "+1.8 pts", "color": "var(--green)", "bench": "32.0% bench"},
    {"label": "APP → FUNDED", "value": "57.5%", "delta": "-0.6 pts", "color": "var(--amber)", "bench": "58.0% bench"},
    {"label": "OVERALL CVR", "value": "1.30%", "delta": "+0.08 pts", "color": "var(--cyan)", "bench": "1.15% bench"},
]

cvr_cards = ""
for i, c in enumerate(_CVR_DATA):
    delay = f"{0.04 * (i + 1):.2f}"
    cvr_cards += f"""
    <div style="display:flex; flex-direction:column; padding:18px; border-radius:14px;
      border:1px solid var(--line); background:var(--panel);
      animation:rise .4s ease-out {delay}s both;">
      <span style="font-family:{_mono}; font-size:9px; letter-spacing:.1em; color:var(--text3);">{c['label']}</span>
      <span style="font-family:{_ff}; font-size:28px; font-weight:600; letter-spacing:-.02em; margin-top:8px;">{c['value']}</span>
      <div style="display:flex; align-items:center; gap:8px; margin-top:6px;">
        <span style="font-family:{_mono}; font-size:11px; font-weight:500; color:{c['color']};">{c['delta']}</span>
        <span style="font-family:{_mono}; font-size:9px; color:var(--text3);">{c['bench']}</span>
      </div>
    </div>"""

st.markdown(f"""
<div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:14px; margin-bottom:18px;">
  {cvr_cards}
</div>
""", unsafe_allow_html=True)

render_chat_drawer(page_key="acq_funnel")
