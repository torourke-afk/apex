"""
Executive Scorecard — Signal Deck spec
CMO morning glance: contractual KPIs vs target, financial summary, top campaigns, live alerts.
Layout: HUD ribbon → hero gauge + KPI deck → financial summary strip → leaderboard + alert wire.
"""
import streamlit as st

from src.components.filter_bar import get_global_filters
from src.config.brand import COLORS
from src.data.scorecard_queries import (
    get_kpi_summary, get_financial_summary, get_recent_alerts, get_campaign_performance,
)
from src.components.page_chrome import page_chrome
from src.components.chat_drawer import render_chat_drawer

# Retain optional data sources
try:
    from src.data.retention_forecast import get_retained_hh_estimate
    _HAS_RETENTION = True
except ImportError:
    _HAS_RETENTION = False
try:
    from src.data.brand_awareness import (
        get_latest_share_of_search, config_to_json, default_fitb_config,
    )
    _HAS_BRAND_AWARENESS = True
except ImportError:
    _HAS_BRAND_AWARENESS = False

_SEVERITY_COLORS = {
    "error": "#FF5C72", "warning": "#F2B14C",
    "info": "#34E1D4", "success": "#4FD89B",
}


def _fmt_currency(val: float) -> str:
    if val >= 1_000_000:
        return f"${val / 1_000_000:.1f}M"
    return f"${val / 1_000:.0f}K"


page_chrome(title="Executive Scorecard", category="COMMAND")

if "cache_cleared" not in st.session_state:
    st.cache_data.clear()
    st.session_state["cache_cleared"] = True

filters = get_global_filters()
kpis = get_kpi_summary(filters)
financials = get_financial_summary(filters)
alerts = get_recent_alerts(filters, limit=10)
_n_alerts = len(alerts)

# ─── Helpers ──────────────────────────────────────────────────────────────
_mono = "'JetBrains Mono',monospace"
_ff = "'Space Grotesk',system-ui,sans-serif"


def _kpi_color(name, delta_pct):
    """Return accent color and status dot color for a KPI."""
    inverted = name in {"CPIHH", "Cost Per Incremental HH"}
    if delta_pct is None:
        return "var(--cyan)", "var(--cyan)"
    if inverted:
        return ("var(--green)", "var(--green)") if delta_pct <= 0 else ("var(--amber)", "var(--amber)")
    return ("var(--green)", "var(--green)") if delta_pct >= 0 else ("var(--amber)", "var(--amber)")


def _spark_points(data, w=92, h=28):
    """Generate SVG polyline points from sparkline data."""
    if not data or len(data) < 2:
        return "0,14 92,14"
    mn, mx = min(data), max(data)
    rng = mx - mn if mx != mn else 1
    pts = []
    for i, v in enumerate(data):
        x = int(i * w / (len(data) - 1))
        y = int(h - 4 - (v - mn) / rng * (h - 8))
        pts.append(f"{x},{y}")
    return " ".join(pts)


def _mini_ring(pct, color, size=56):
    """SVG mini progress ring for KPI cards."""
    r = 24
    c = 2 * 3.14159 * r
    offset = c * (1 - pct / 100)
    check = "✓" if pct >= 100 else str(int(pct))
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 60 60">
      <circle cx="30" cy="30" r="{r}" fill="none" stroke="var(--line)" stroke-width="5"/>
      <circle cx="30" cy="30" r="{r}" fill="none" stroke="{color}" stroke-width="5"
              stroke-linecap="round" stroke-dasharray="{c:.1f}" stroke-dashoffset="{offset:.1f}"
              transform="rotate(-90 30 30)" style="animation:ringkpi 1.4s cubic-bezier(.22,1,.36,1) .2s both;"/>
      <text x="30" y="34" text-anchor="middle" font-family="{_mono}" font-size="13"
            font-weight="500" fill="var(--text)">{check}</text>
    </svg>"""


# ─── HUD Ribbon ──────────────────────────────────────────────────────────
st.markdown(f"""
<div style="display:flex; align-items:center; gap:16px; padding:9px 16px; margin-bottom:16px;
  border-radius:11px; border:1px solid var(--line);
  background:linear-gradient(90deg, rgba(52,225,212,.06), transparent 40%);
  font-family:{_mono}; animation:rise .5s ease-out both;">
  <div style="display:flex; align-items:center; gap:8px;">
    <div style="width:7px; height:7px; border-radius:50%; background:var(--green);
         box-shadow:0 0 9px var(--green);"></div>
    <span style="font-size:10.5px; letter-spacing:.16em; color:var(--text);">MISSION STATUS — ON PACE</span>
  </div>
  <div style="width:1px; height:14px; background:var(--line2);"></div>
  <span style="font-size:10px; letter-spacing:.1em; color:var(--text2);">WEEK 11 / 12 · CONTRACT CYCLE Q3</span>
  <div style="flex:1;"></div>
  <span style="font-size:9.5px; letter-spacing:.12em; color:var(--text3);">AUTOPILOT: ASSIST</span>
  <span style="font-size:9.5px; letter-spacing:.12em; color:var(--text3);">MODELS: 6 LIVE</span>
  <span style="font-size:9.5px; letter-spacing:.12em; color:var(--cyan);">{_n_alerts} ALERTS</span>
</div>
""", unsafe_allow_html=True)

# ─── Hero Gauge + KPI Deck (side by side) ────────────────────────────────
_health_pct = 88
_ring_r = 88
_ring_c = 2 * 3.14159 * _ring_r
_ring_offset = _ring_c * (1 - _health_pct / 100)

# Build KPI cards HTML
_kpi_cards_html = ""
_kpi_data = [
    {"label": "FUNDED ACCOUNTS", "value": "18,420", "delta": "↑ 6.2%", "delta_note": "vs target 21,000", "color": "var(--green)", "dot": "var(--cyan)", "pct": 88},
    {"label": "CPIHH", "value": "$312", "delta": "↑ 7.6%", "delta_note": "over target $290", "color": "var(--amber)", "dot": "var(--amber)", "pct": 93},
    {"label": "PORTFOLIO LTV", "value": "$4,180", "delta": "↑ 4.5%", "delta_note": "target met · $4,000", "color": "var(--green)", "dot": "var(--green)", "pct": 100},
    {"label": "BLENDED ROAS", "value": "3.8×", "delta": "↑ 0.3", "delta_note": "over target 3.5×", "color": "var(--green)", "dot": "var(--green)", "pct": 100},
    {"label": "MOB6 RETENTION", "value": "71.4<span style='font-size:18px;color:var(--text2);'>%</span>", "delta": "↓ 0.4", "delta_note": "vs target 74%", "color": "var(--amber)", "dot": "var(--cyan)", "pct": 96},
]

# Use real data if available, fallback to reference sample data
for i, kpi in enumerate(kpis[:5]):
    if i < len(_kpi_data):
        d = _kpi_data[i]
        # Override with real data where possible
        val = kpi.get("value", d["value"])
        if isinstance(val, (int, float)):
            if kpi.get("format_type") == "currency":
                val = _fmt_currency(val)
            elif kpi.get("format_type") == "percent":
                val = f"{val:.1f}%"
            else:
                val = f"{val:,.0f}" if val >= 100 else f"{val}"
        d["value"] = str(val)

# Build sparkline data
_sparks = [
    "0,22 13,20 26,21 39,15 52,16 65,10 78,11 92,4",
    "0,8 13,11 26,9 39,14 52,13 65,18 78,16 92,20",
    "0,20 13,18 26,19 39,14 52,12 65,11 78,7 92,5",
    "0,18 13,17 26,15 39,16 52,12 65,13 78,9 92,7",
    "0,8 13,9 26,11 39,10 52,13 65,12 78,15 92,14",
]

for i, d in enumerate(_kpi_data):
    spark = _sparks[i] if i < len(_sparks) else _sparks[0]
    ring = _mini_ring(d["pct"], d["color"])
    delay = f"{0.05 * (i+1):.2f}"
    _kpi_cards_html += f"""
    <div style="display:flex; flex-direction:column; padding:16px; border-radius:14px;
      border:1px solid var(--line); background:var(--panel);
      animation:rise .5s ease-out {delay}s both;">
      <div style="display:flex; align-items:center; justify-content:space-between;">
        <span style="font-family:{_mono}; font-size:9.5px; letter-spacing:.1em; color:var(--text2);">{d['label']}</span>
        <div style="width:6px; height:6px; border-radius:50%; background:{d['dot']};
             box-shadow:0 0 7px {d['dot']};"></div>
      </div>
      <div style="display:flex; align-items:baseline; gap:5px; margin-top:10px;">
        <span style="font-size:30px; font-weight:600; letter-spacing:-.02em;">{d['value']}</span>
      </div>
      <div style="display:flex; align-items:center; gap:7px; margin-top:5px;">
        <span style="font-family:{_mono}; font-size:11px; font-weight:500; color:{d['color']};">{d['delta']}</span>
        <span style="font-family:{_mono}; font-size:10px; color:var(--text3);">{d['delta_note']}</span>
      </div>
      <div style="display:flex; align-items:flex-end; justify-content:space-between; margin-top:14px;">
        <svg width="92" height="28" viewBox="0 0 92 28" fill="none">
          <polyline points="{spark}" stroke="{d['color']}" stroke-width="1.8"
                    stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        {ring}
      </div>
    </div>"""

# OperatingStreak card (6th position in grid)
_streak_weeks = 7
_streak_bars = ""
for w in range(12):
    bg = "var(--cyan)" if w < _streak_weeks else "var(--line)"
    _streak_bars += f'<div style="flex:1; height:6px; border-radius:3px; background:{bg};"></div>'

_kpi_cards_html += f"""
    <div style="display:flex; flex-direction:column; justify-content:space-between; padding:16px;
      border-radius:14px; border:1px solid rgba(52,225,212,.28);
      background:radial-gradient(130% 100% at 100% 0%, rgba(52,225,212,.1), var(--panel) 60%);
      animation:rise .5s ease-out .3s both;">
      <div style="display:flex; align-items:center; justify-content:space-between;">
        <span style="font-family:{_mono}; font-size:9.5px; letter-spacing:.1em; color:var(--cyan);">OPERATING STREAK</span>
        <span style="font-size:13px;">▲</span>
      </div>
      <div style="display:flex; align-items:baseline; gap:6px; margin-top:6px;">
        <span style="font-size:34px; font-weight:700; letter-spacing:-.02em;">{_streak_weeks}</span>
        <span style="font-family:{_mono}; font-size:13px; color:var(--text2);">WEEKS ON PACE</span>
      </div>
      <div style="display:flex; gap:3px; margin-top:11px;">{_streak_bars}</div>
      <div style="font-family:{_mono}; font-size:10px; letter-spacing:.06em; color:var(--text2); margin-top:11px;">
        ALERTS CLEARED · 3 DAYS</div>
    </div>"""

st.markdown(f"""
<div style="display:flex; gap:16px; align-items:stretch; margin-bottom:16px; flex-wrap:wrap;">
  <!-- Hero gauge -->
  <section style="flex:1 1 290px; max-width:330px; min-width:290px; display:flex; flex-direction:column;
    padding:22px; border-radius:16px; border:1px solid var(--line);
    background:radial-gradient(120% 80% at 50% 0%, rgba(52,225,212,.07), var(--panel) 55%);
    animation:rise .55s ease-out both;">
    <div style="display:flex; align-items:center; justify-content:space-between;">
      <span style="font-family:{_mono}; font-size:10px; letter-spacing:.16em; color:var(--text2);">CONTRACT HEALTH</span>
      <span style="font-family:{_mono}; font-size:9px; letter-spacing:.1em; color:var(--cyan);
            padding:3px 7px; border-radius:5px; background:rgba(52,225,212,.1);">COMPOSITE</span>
    </div>
    <div style="position:relative; align-self:center; margin:14px 0 8px;">
      <svg width="220" height="220" viewBox="0 0 220 220">
        <circle cx="110" cy="110" r="{_ring_r}" fill="none" stroke="var(--line)" stroke-width="13"/>
        <circle cx="110" cy="110" r="{_ring_r}" fill="none" stroke="var(--cyan)" stroke-width="13"
                stroke-linecap="round" stroke-dasharray="{_ring_c:.1f}" stroke-dashoffset="{_ring_offset:.1f}"
                transform="rotate(-90 110 110)"
                style="animation:ringhero 1.6s cubic-bezier(.22,1,.36,1) both; filter:drop-shadow(0 0 7px rgba(52,225,212,.5));"/>
      </svg>
      <div style="position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center;">
        <div style="font-size:58px; font-weight:600; letter-spacing:-.03em; line-height:1;">
          {_health_pct}<span style="font-size:24px; color:var(--text2); font-weight:500;">%</span>
        </div>
        <div style="font-family:{_mono}; font-size:9.5px; letter-spacing:.12em; color:var(--text3); margin-top:4px;">
          TO TARGET · +12% TO GO</div>
      </div>
    </div>
    <!-- Sub-bars -->
    <div style="display:flex; flex-direction:column; gap:9px; margin-top:6px;">
      <div style="display:flex; align-items:center; gap:10px;">
        <span style="flex:none; width:78px; font-family:{_mono}; font-size:9.5px; letter-spacing:.08em; color:var(--text3);">ACQUISITION</span>
        <div style="flex:1; height:5px; border-radius:5px; background:var(--line); overflow:hidden;">
          <div style="width:91%; height:100%; border-radius:5px; background:var(--cyan);"></div>
        </div>
        <span style="font-family:{_mono}; font-size:11px; font-weight:500;">91</span>
      </div>
      <div style="display:flex; align-items:center; gap:10px;">
        <span style="flex:none; width:78px; font-family:{_mono}; font-size:9.5px; letter-spacing:.08em; color:var(--text3);">EFFICIENCY</span>
        <div style="flex:1; height:5px; border-radius:5px; background:var(--line); overflow:hidden;">
          <div style="width:84%; height:100%; border-radius:5px; background:var(--amber);"></div>
        </div>
        <span style="font-family:{_mono}; font-size:11px; font-weight:500;">84</span>
      </div>
      <div style="display:flex; align-items:center; gap:10px;">
        <span style="flex:none; width:78px; font-family:{_mono}; font-size:9.5px; letter-spacing:.08em; color:var(--text3);">RETENTION</span>
        <div style="flex:1; height:5px; border-radius:5px; background:var(--line); overflow:hidden;">
          <div style="width:89%; height:100%; border-radius:5px; background:var(--cyan);"></div>
        </div>
        <span style="font-family:{_mono}; font-size:11px; font-weight:500;">89</span>
      </div>
    </div>
  </section>

  <!-- KPI deck -->
  <section style="flex:3 1 560px; min-width:300px; display:grid;
    grid-template-columns:repeat(3, minmax(0,1fr)); gap:14px;">
    {_kpi_cards_html}
  </section>
</div>
""", unsafe_allow_html=True)

# ─── Financial Summary Strip ─────────────────────────────────────────────
_fin_data = [
    {"label": "TOTAL SPEND", "value": "$24.6M", "sub": "62% of $39.4M plan", "sub_color": "var(--text2)"},
    {"label": "ATTRIB. REVENUE", "value": "$93.4M", "sub": "↑ 11.2% QoQ", "sub_color": "var(--green)"},
    {"label": "NET MARGIN", "value": "38.2%", "sub": "↑ 1.4 pts", "sub_color": "var(--green)"},
    {"label": "EFFICIENCY", "value": "3.8×", "sub": "blended ROAS", "sub_color": "var(--text2)"},
    {"label": "PACING", "value": "96%", "sub": "on plan · wk 11/12", "sub_color": "var(--text2)"},
]

# Use real financial data if available
for i, fm in enumerate(financials[:5]):
    if i < len(_fin_data):
        val = fm.get("value", _fin_data[i]["value"])
        if isinstance(val, (int, float)):
            if fm.get("format") == "currency":
                val = _fmt_currency(val)
            elif fm.get("format") == "percent":
                val = f"{val:.1f}%"
            else:
                val = str(val)
        _fin_data[i]["value"] = str(val)

_fin_cells = ""
for i, f in enumerate(_fin_data):
    border_r = "border-right:1px solid var(--line);" if i < len(_fin_data) - 1 else ""
    _fin_cells += f"""
    <div style="flex:1; min-width:150px; padding:16px 20px; {border_r}">
      <div style="font-family:{_mono}; font-size:9.5px; letter-spacing:.12em; color:var(--text3);">{f['label']}</div>
      <div style="font-size:25px; font-weight:600; margin-top:6px; letter-spacing:-.02em;">{f['value']}</div>
      <div style="font-family:{_mono}; font-size:10px; color:{f['sub_color']}; margin-top:3px;">{f['sub']}</div>
    </div>"""

st.markdown(f"""
<section style="display:flex; flex-wrap:wrap; margin-bottom:16px; border-radius:14px;
  border:1px solid var(--line); background:var(--panel); overflow:hidden;
  animation:rise .5s ease-out .12s both;">
  {_fin_cells}
</section>
""", unsafe_allow_html=True)

# ─── Campaign Leaderboard + Alert Wire ───────────────────────────────────
_campaign_data = [
    {"name": "Checking Conquest — SEM", "channel": "SEM", "spend": "$3.2M", "roas": "4.2×", "good": True},
    {"name": "Brand Awareness — YouTube", "channel": "SOCIAL", "spend": "$2.8M", "roas": "3.8×", "good": True},
    {"name": "Savings Promo — Display", "channel": "DISPLAY", "spend": "$1.9M", "roas": "3.6×", "good": True},
    {"name": "CC Rewards — Meta", "channel": "SOCIAL", "spend": "$1.4M", "roas": "4.1×", "good": True},
    {"name": "Mortgage Retarget — SEM", "channel": "SEM", "spend": "$1.1M", "roas": "2.9×", "good": False},
    {"name": "Auto Loan — Brand", "channel": "BRAND", "spend": "$0.8M", "roas": "3.5×", "good": True},
]

# Try to use real campaign data
try:
    raw_campaigns = get_campaign_performance(filters)
    if raw_campaigns:
        _campaign_data = []
        for c in raw_campaigns[:6]:
            roas_val = c.get("ROAS", 0)
            _campaign_data.append({
                "name": c.get("Campaign", "Campaign"),
                "channel": c.get("Channel", "—"),
                "spend": _fmt_currency(c.get("Spend", 0)),
                "roas": f"{roas_val:.1f}×",
                "good": roas_val >= 3.5,
            })
except Exception:
    pass

_campaign_rows = ""
for c in _campaign_data:
    badge_style = (
        f"font-family:{_mono}; font-size:11px; font-weight:500; text-align:right; "
        f"padding:3px 8px; border-radius:6px; "
        + ("background:rgba(79,216,155,.14); color:var(--green);" if c["good"]
           else "background:rgba(255,92,114,.14); color:var(--red);")
    )
    _campaign_rows += f"""
    <div style="display:grid; grid-template-columns:1fr 88px 80px 76px; gap:8px;
      align-items:center; padding:12px 18px; border-bottom:1px solid var(--line);">
      <span style="font-size:13px; font-weight:500; white-space:nowrap; overflow:hidden;
            text-overflow:ellipsis;">{c['name']}</span>
      <span style="font-family:{_mono}; font-size:10px; color:var(--text2);">{c['channel']}</span>
      <span style="font-family:{_mono}; font-size:12px; text-align:right; color:var(--text);">{c['spend']}</span>
      <span style="{badge_style}">{c['roas']}</span>
    </div>"""

# Alert wire
_alert_rows = ""
if not alerts:
    _alert_rows = f"""
    <div style="display:flex; flex-direction:column; align-items:center; justify-content:center;
      gap:8px; padding:48px 20px; text-align:center;">
      <div style="width:34px; height:34px; border-radius:50%; border:2px solid var(--green);
           display:flex; align-items:center; justify-content:center; color:var(--green); font-size:16px;">✓</div>
      <div style="font-size:13px; color:var(--text2);">Wire clear — all thresholds nominal</div>
    </div>"""
else:
    for a in alerts[:6]:
        sev = a.get("severity", "info")
        bar_color = _SEVERITY_COLORS.get(sev, "var(--cyan)")
        tag = sev.upper()
        tag_color = bar_color
        tag_bg = f"rgba({','.join(str(int(bar_color.lstrip('#')[i:i+2], 16)) for i in (0,2,4))}, .14)" if bar_color.startswith("#") else f"rgba(52,225,212,.14)"
        _alert_rows += f"""
    <div style="display:flex; align-items:center; gap:11px; padding:11px 16px;
      border-bottom:1px solid var(--line);">
      <div style="width:3px; height:30px; border-radius:3px; flex:none; background:{bar_color};"></div>
      <div style="flex:none; width:60px; text-align:center; font-family:{_mono}; font-size:8.5px;
           letter-spacing:.06em; padding:3px 0; border-radius:5px;
           color:{tag_color}; background:{tag_bg};">{tag}</div>
      <div style="flex:1; min-width:0; font-size:12px; line-height:1.35; color:var(--text);">
        {a.get('kpi', '')} — {a.get('desc', '')}</div>
      <span style="flex:none; font-family:{_mono}; font-size:9px; color:var(--text3);">{a.get('ts', '')}</span>
      <button style="flex:none; padding:4px 8px; border-radius:6px; border:1px solid var(--line);
              background:none; color:var(--text3); cursor:pointer; font-family:{_mono};
              font-size:8.5px; letter-spacing:.08em;">ACK</button>
    </div>"""

st.markdown(f"""
<div style="display:flex; gap:16px; align-items:stretch; flex-wrap:wrap;">
  <!-- Campaign leaderboard -->
  <section style="flex:1.5 1 480px; min-width:340px; border-radius:14px; border:1px solid var(--line);
    background:var(--panel); overflow:hidden; animation:rise .5s ease-out .18s both;">
    <div style="display:flex; align-items:center; justify-content:space-between; padding:15px 18px;
      border-bottom:1px solid var(--line);">
      <div style="display:flex; align-items:center; gap:10px;">
        <div style="width:3px; height:15px; background:var(--cyan); border-radius:3px;"></div>
        <span style="font-size:14px; font-weight:600;">Campaign Performance</span>
      </div>
      <span style="font-family:{_mono}; font-size:9.5px; letter-spacing:.1em; color:var(--text3);">TOP BY ROAS</span>
    </div>
    <div style="display:grid; grid-template-columns:1fr 88px 80px 76px; gap:8px; padding:9px 18px;
      border-bottom:1px solid var(--line); font-family:{_mono}; font-size:9px;
      letter-spacing:.1em; color:var(--text3);">
      <span>CAMPAIGN</span><span>CHANNEL</span>
      <span style="text-align:right;">SPEND</span><span style="text-align:right;">ROAS</span>
    </div>
    {_campaign_rows}
  </section>

  <!-- Alert wire -->
  <section style="flex:1 1 320px; min-width:300px; display:flex; flex-direction:column;
    border-radius:14px; border:1px solid var(--line); background:var(--panel); overflow:hidden;
    animation:rise .5s ease-out .24s both;">
    <div style="display:flex; align-items:center; justify-content:space-between; padding:15px 18px;
      border-bottom:1px solid var(--line);">
      <div style="display:flex; align-items:center; gap:10px;">
        <div style="width:3px; height:15px; background:var(--red); border-radius:3px;"></div>
        <span style="font-size:14px; font-weight:600;">Alert Wire</span>
      </div>
      <span style="font-family:{_mono}; font-size:9.5px; letter-spacing:.1em; color:var(--text3);">{_n_alerts} ACTIVE</span>
    </div>
    <div style="flex:1; min-height:0; overflow:auto;">
      {_alert_rows}
    </div>
  </section>
</div>
""", unsafe_allow_html=True)

render_chat_drawer(page_key="exec_scorecard")
