"""
Performance Media -- Signal Deck spec
Paid performance channels: channel performance table, creative cards grid, message theme resonance.
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
        "name": "SEM",
        "dot": "var(--cyan)",
        "spend": "$3.21M",
        "cpihh": "$278",
        "cvr": "5.5%",
        "roas": "4.2x",
        "spark": "0,18 10,14 20,12 32,10 42,8 54,6 64,4",
    },
    {
        "name": "Paid Social",
        "dot": "var(--green)",
        "spend": "$1.14M",
        "cpihh": "$345",
        "cvr": "3.2%",
        "roas": "3.1x",
        "spark": "0,14 10,12 20,14 32,10 42,12 54,8 64,6",
    },
    {
        "name": "Display",
        "dot": "var(--amber)",
        "spend": "$820K",
        "cpihh": "$490",
        "cvr": "1.1%",
        "roas": "2.4x",
        "spark": "0,10 10,12 20,14 32,16 42,14 54,16 64,18",
    },
    {
        "name": "Retargeting",
        "dot": "var(--text2)",
        "spend": "$380K",
        "cpihh": "$195",
        "cvr": "6.8%",
        "roas": "5.1x",
        "spark": "0,20 10,16 20,14 32,10 42,8 54,6 64,2",
    },
]

_CREATIVES = [
    {
        "title": "Checking Freedom 30s",
        "format": "VIDEO",
        "fatigue": "Fresh",
        "fatigue_color": "var(--green)",
        "ctr": "3.8%",
        "cvr": "5.2%",
        "spend": "$420K",
        "gradient": "linear-gradient(135deg, rgba(52,225,212,.15), rgba(79,216,155,.08))",
    },
    {
        "title": "Savings Rate Hero",
        "format": "STATIC",
        "fatigue": "Fresh",
        "fatigue_color": "var(--green)",
        "ctr": "2.1%",
        "cvr": "4.8%",
        "spend": "$310K",
        "gradient": "linear-gradient(135deg, rgba(242,177,76,.12), rgba(255,92,114,.06))",
    },
    {
        "title": "Mobile App Install",
        "format": "CAROUSEL",
        "fatigue": "Aging",
        "fatigue_color": "var(--amber)",
        "ctr": "1.9%",
        "cvr": "3.1%",
        "spend": "$280K",
        "gradient": "linear-gradient(135deg, rgba(79,216,155,.12), rgba(52,225,212,.06))",
    },
    {
        "title": "CD Rate Promo Q3",
        "format": "STATIC",
        "fatigue": "Fatigued",
        "fatigue_color": "var(--red)",
        "ctr": "0.8%",
        "cvr": "1.4%",
        "spend": "$190K",
        "gradient": "linear-gradient(135deg, rgba(255,92,114,.12), rgba(242,177,76,.06))",
    },
    {
        "title": "HELOC Awareness",
        "format": "VIDEO",
        "fatigue": "Fresh",
        "fatigue_color": "var(--green)",
        "ctr": "2.9%",
        "cvr": "4.1%",
        "spend": "$260K",
        "gradient": "linear-gradient(135deg, rgba(52,225,212,.12), rgba(79,216,155,.1))",
    },
    {
        "title": "Rewards CC Retarget",
        "format": "RICH MEDIA",
        "fatigue": "Aging",
        "fatigue_color": "var(--amber)",
        "ctr": "1.5%",
        "cvr": "2.6%",
        "spend": "$175K",
        "gradient": "linear-gradient(135deg, rgba(242,177,76,.15), rgba(52,225,212,.06))",
    },
]

_THEMES = [
    {"name": "Rate Advantage", "score": 82, "color": "var(--cyan)"},
    {"name": "Digital Convenience", "score": 76, "color": "var(--green)"},
    {"name": "Trust & Security", "score": 71, "color": "var(--cyan)"},
    {"name": "Rewards & Cash Back", "score": 64, "color": "var(--amber)"},
    {"name": "Local Community", "score": 58, "color": "var(--amber)"},
    {"name": "Life Events", "score": 45, "color": "var(--text3)"},
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_mono = "'JetBrains Mono',monospace"
_ff = "'Space Grotesk',system-ui,sans-serif"


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

page_chrome(title="Performance Media", category="CHANNELS")
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


# -- Creative Performance Cards -----------------------------------------------

_creative_cards = ""
for i, cr in enumerate(_CREATIVES):
    delay = f"{0.04 * (i + 1) + 0.08:.2f}"
    _creative_cards += f"""
    <div style="border-radius:14px; border:1px solid var(--line); background:var(--panel);
      overflow:hidden; animation:rise .4s ease-out {delay}s both;">
      <!-- Thumbnail placeholder -->
      <div style="height:118px; background:{cr['gradient']}; position:relative;">
        <!-- Format badge -->
        <div style="position:absolute; top:10px; left:10px; padding:3px 8px; border-radius:5px;
          background:rgba(0,0,0,.55); backdrop-filter:blur(6px);
          font-family:{_mono}; font-size:8.5px; letter-spacing:.08em; color:var(--text);">
          {cr['format']}
        </div>
        <!-- Fatigue indicator -->
        <div style="position:absolute; top:10px; right:10px; padding:3px 8px; border-radius:5px;
          background:rgba(0,0,0,.55); backdrop-filter:blur(6px);
          font-family:{_mono}; font-size:8.5px; letter-spacing:.06em; color:{cr['fatigue_color']};">
          {cr['fatigue']}
        </div>
      </div>
      <!-- Card body -->
      <div style="padding:14px 16px;">
        <div style="font-size:13px; font-weight:600; color:var(--text); margin-bottom:12px;
          white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{cr['title']}</div>
        <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:4px;">
          <div>
            <div style="font-family:{_mono}; font-size:8.5px; letter-spacing:.08em; color:var(--text3); margin-bottom:3px;">CTR</div>
            <div style="font-family:{_mono}; font-size:14px; font-weight:600; color:var(--text); font-variant-numeric:tabular-nums;">{cr['ctr']}</div>
          </div>
          <div>
            <div style="font-family:{_mono}; font-size:8.5px; letter-spacing:.08em; color:var(--text3); margin-bottom:3px;">CVR</div>
            <div style="font-family:{_mono}; font-size:14px; font-weight:600; color:var(--text); font-variant-numeric:tabular-nums;">{cr['cvr']}</div>
          </div>
          <div>
            <div style="font-family:{_mono}; font-size:8.5px; letter-spacing:.08em; color:var(--text3); margin-bottom:3px;">SPEND</div>
            <div style="font-family:{_mono}; font-size:14px; font-weight:600; color:var(--text); font-variant-numeric:tabular-nums;">{cr['spend']}</div>
          </div>
        </div>
      </div>
    </div>"""

st.markdown(f"""
<section style="margin-bottom:16px; animation:rise .4s ease-out .06s both;">
  <!-- Section header -->
  <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">
    <div style="width:3px; height:15px; background:var(--cyan); border-radius:3px;"></div>
    <span style="font-size:14px; font-weight:600; color:var(--text);">Creative Performance</span>
    <span style="font-family:{_mono}; font-size:9.5px; letter-spacing:.1em; color:var(--text3); margin-left:auto;">ACTIVE UNITS</span>
  </div>
  <!-- Card grid -->
  <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:14px;">
    {_creative_cards}
  </div>
</section>
""", unsafe_allow_html=True)


# -- Message Theme Resonance --------------------------------------------------

_max_score = max(t["score"] for t in _THEMES) if _THEMES else 100
_theme_rows = ""
for i, t in enumerate(_THEMES):
    bar_pct = (t["score"] / _max_score) * 100
    delay = f"{0.04 * (i + 1) + 0.16:.2f}"
    _theme_rows += f"""
    <div style="display:flex; align-items:center; gap:10px; padding:8px 0;
      animation:rise .4s ease-out {delay}s both;">
      <span style="flex:none; width:160px; font-size:12.5px; font-weight:500; color:var(--text);
        white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{t['name']}</span>
      <div style="flex:1; height:8px; border-radius:4px; background:var(--line); overflow:hidden;">
        <div style="width:{bar_pct}%; height:100%; border-radius:4px; background:{t['color']};
          transition:width .6s ease;"></div>
      </div>
      <span style="flex:none; width:54px; text-align:right; font-family:{_mono};
        font-size:13px; font-weight:600; color:{t['color']}; font-variant-numeric:tabular-nums;">
        {t['score']}</span>
    </div>"""

st.markdown(f"""
<section style="border-radius:14px; border:1px solid var(--line); background:var(--panel);
  overflow:hidden; margin-bottom:16px; animation:rise .4s ease-out .14s both;">
  <div style="display:flex; align-items:center; justify-content:space-between; padding:15px 18px;
    border-bottom:1px solid var(--line);">
    <div style="display:flex; align-items:center; gap:10px;">
      <div style="width:3px; height:15px; background:var(--cyan); border-radius:3px;"></div>
      <span style="font-size:14px; font-weight:600; color:var(--text);">Message Theme Resonance</span>
    </div>
    <span style="font-family:{_mono}; font-size:9.5px; letter-spacing:.1em; color:var(--text3);">ENGAGEMENT SCORE</span>
  </div>
  <div style="padding:10px 18px 16px;">
    {_theme_rows}
  </div>
</section>
""", unsafe_allow_html=True)


render_chat_drawer(page_key="perf_media")
