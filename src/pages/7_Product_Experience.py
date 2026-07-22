"""
Product & Conversion -- Signal Deck spec
Product line performance table, conversion funnels by product, testing velocity KPIs.
"""
import streamlit as st

from src.components.filter_bar import get_global_filters
from src.components.page_chrome import page_chrome
from src.components.chat_drawer import render_chat_drawer

# ---------------------------------------------------------------------------
# Seed / fallback data
# ---------------------------------------------------------------------------

_PRODUCTS = [
    {"name": "Checking",      "funded": "8,420", "cpihh": "$312",  "ltv": "$4,180",  "margin": 34.2},
    {"name": "Savings",       "funded": "4,180", "cpihh": "$189",  "ltv": "$2,640",  "margin": 28.1},
    {"name": "Credit Card",   "funded": "3,240", "cpihh": "$445",  "ltv": "$6,320",  "margin": 22.7},
    {"name": "Personal Loan", "funded": "1,680", "cpihh": "$520",  "ltv": "$3,890",  "margin": 18.4},
    {"name": "Mortgage",      "funded": "890",   "cpihh": "$680",  "ltv": "$12,400", "margin": 12.1},
    {"name": "Auto Loan",     "funded": "720",   "cpihh": "$390",  "ltv": "$3,100",  "margin": 8.6},
]

_FUNNELS = [
    {
        "product": "Checking",
        "funded_val": "2.8K",
        "stages": [
            {"label": "Visits",   "value": "142K", "width": 100},
            {"label": "Leads",    "value": "8.2K", "width": 58},
            {"label": "Apps",     "value": "4.1K", "width": 29},
            {"label": "Approved", "value": "3.2K", "width": 23},
            {"label": "Funded",   "value": "2.8K", "width": 20},
        ],
    },
    {
        "product": "Savings",
        "funded_val": "2.6K",
        "stages": [
            {"label": "Visits",   "value": "98K",  "width": 100},
            {"label": "Leads",    "value": "5.4K", "width": 55},
            {"label": "Apps",     "value": "3.8K", "width": 39},
            {"label": "Approved", "value": "3.1K", "width": 32},
            {"label": "Funded",   "value": "2.6K", "width": 27},
        ],
    },
    {
        "product": "Credit Card",
        "funded_val": "1.6K",
        "stages": [
            {"label": "Visits",   "value": "76K",  "width": 100},
            {"label": "Leads",    "value": "4.8K", "width": 63},
            {"label": "Apps",     "value": "2.9K", "width": 38},
            {"label": "Approved", "value": "2.1K", "width": 28},
            {"label": "Funded",   "value": "1.6K", "width": 21},
        ],
    },
]

_TESTING_KPIS = [
    {"label": "TESTS RUNNING", "value": "12",    "color": "var(--text)"},
    {"label": "WIN RATE",      "value": "68%",   "color": "var(--green)"},
    {"label": "AVG LIFT",      "value": "+3.2%", "color": "var(--green)"},
    {"label": "TESTS WON",     "value": "8",     "color": "var(--green)"},
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_mono = "'JetBrains Mono',monospace"
_ff = "'Space Grotesk',system-ui,sans-serif"


def _margin_badge(margin: float) -> str:
    """Return inline style string for margin badge color."""
    if margin >= 20:
        return "background:rgba(79,216,155,.14); color:var(--green);"
    if margin >= 10:
        return "background:rgba(242,177,76,.14); color:var(--amber);"
    return "background:rgba(255,92,114,.14); color:var(--red);"


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

page_chrome(title="Product Experience", category="PRODUCT")
filters = get_global_filters()


# -- Product Line Performance Table -------------------------------------------

_product_rows = ""
for i, p in enumerate(_PRODUCTS):
    delay = f"{0.04 * (i + 1):.2f}"
    badge = _margin_badge(p["margin"])
    _product_rows += f"""
    <div style="display:grid; grid-template-columns:1.3fr 96px 96px 96px 110px;
      gap:8px; align-items:center; padding:11px 18px; border-bottom:1px solid var(--line);
      animation:rise .4s ease-out {delay}s both;">
      <span style="font-size:13px; font-weight:500; color:var(--text);">{p['name']}</span>
      <span style="font-family:{_mono}; font-size:12px; color:var(--text); text-align:right;">{p['funded']}</span>
      <span style="font-family:{_mono}; font-size:12px; color:var(--text); text-align:right;">{p['cpihh']}</span>
      <span style="font-family:{_mono}; font-size:12px; color:var(--text); text-align:right;">{p['ltv']}</span>
      <div style="display:flex; justify-content:flex-end;">
        <span style="font-family:{_mono}; font-size:11px; font-weight:500; padding:3px 8px;
          border-radius:6px; {badge}">{p['margin']}%</span>
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
      <span style="font-size:14px; font-weight:600; color:var(--text);">Product Line Performance</span>
    </div>
  </div>
  <!-- Column headers -->
  <div style="display:grid; grid-template-columns:1.3fr 96px 96px 96px 110px;
    gap:8px; padding:9px 18px; border-bottom:1px solid var(--line);
    font-family:{_mono}; font-size:9px; letter-spacing:.1em; color:var(--text3);">
    <span>PRODUCT</span>
    <span style="text-align:right;">FUNDED</span>
    <span style="text-align:right;">CPIHH</span>
    <span style="text-align:right;">LTV</span>
    <span style="text-align:right;">MARGIN</span>
  </div>
  {_product_rows}
</section>
""", unsafe_allow_html=True)


# -- Conversion Funnels -------------------------------------------------------

_funnel_cards = ""
for i, funnel in enumerate(_FUNNELS):
    delay = f"{0.04 * (i + 1) + 0.08:.2f}"

    stages_html = ""
    for j, stage in enumerate(funnel["stages"]):
        opacity = 1.0 - (j * 0.15)
        stages_html += f"""
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
          <span style="flex:none; width:58px; font-family:{_mono}; font-size:9px;
            letter-spacing:.04em; color:var(--text3);">{stage['label']}</span>
          <div style="flex:1; height:6px; border-radius:4px; background:var(--line);">
            <div style="width:{stage['width']}%; height:100%; border-radius:4px;
              background:var(--cyan); opacity:{opacity:.2f};"></div>
          </div>
          <span style="flex:none; width:38px; font-family:{_mono}; font-size:10px;
            color:var(--text); text-align:right;">{stage['value']}</span>
        </div>"""

    _funnel_cards += f"""
    <div style="padding:16px; border-radius:14px; border:1px solid var(--line);
      background:var(--panel); animation:rise .4s ease-out {delay}s both;">
      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px;">
        <span style="font-size:13px; font-weight:600; color:var(--text);">{funnel['product']}</span>
        <span style="font-family:{_mono}; font-size:13px; font-weight:500; color:var(--cyan);">{funnel['funded_val']}</span>
      </div>
      {stages_html}
    </div>"""

st.markdown(f"""
<section style="margin-bottom:16px; animation:rise .4s ease-out .06s both;">
  <!-- Header -->
  <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">
    <div style="width:3px; height:15px; background:var(--cyan); border-radius:3px;"></div>
    <span style="font-size:14px; font-weight:600; color:var(--text);">Conversion Funnels</span>
    <span style="font-family:{_mono}; font-size:9.5px; letter-spacing:.1em; color:var(--text3); margin-left:4px;">BY PRODUCT LINE</span>
  </div>
  <!-- Funnel grid -->
  <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:14px;">
    {_funnel_cards}
  </div>
</section>
""", unsafe_allow_html=True)


# -- Testing Velocity ---------------------------------------------------------

_testing_cards = ""
for i, kpi in enumerate(_TESTING_KPIS):
    delay = f"{0.04 * (i + 1) + 0.16:.2f}"
    _testing_cards += f"""
    <div style="display:flex; flex-direction:column; padding:16px; border-radius:14px;
      border:1px solid var(--line); background:var(--panel);
      animation:rise .4s ease-out {delay}s both;">
      <span style="font-family:{_mono}; font-size:9px; letter-spacing:.1em; color:var(--text3);">{kpi['label']}</span>
      <span style="font-size:24px; font-weight:600; color:{kpi['color']}; margin-top:8px;
        letter-spacing:-.02em;">{kpi['value']}</span>
    </div>"""

st.markdown(f"""
<section style="margin-bottom:16px; animation:rise .4s ease-out .14s both;">
  <!-- Header -->
  <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">
    <div style="width:3px; height:15px; background:var(--cyan); border-radius:3px;"></div>
    <span style="font-size:14px; font-weight:600; color:var(--text);">Testing Velocity</span>
    <span style="font-family:{_mono}; font-size:9.5px; letter-spacing:.1em; color:var(--text3); margin-left:4px;">LAST 30 DAYS</span>
  </div>
  <!-- KPI grid -->
  <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:14px;">
    {_testing_cards}
  </div>
</section>
""", unsafe_allow_html=True)


render_chat_drawer(page_key="product_exp")
