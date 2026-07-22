"""
Spend & Budget — Signal Deck design system
-------------------------------------------
Streamlit page rendering the Spend & Budget surface with pure HTML/CSS
matching the Signal Deck tokens exactly (CSS custom properties).
"""

import streamlit as st

from src.components.page_chrome import page_chrome
from src.components.chat_drawer import render_chat_drawer
from src.components.filter_bar import get_global_filters

# ── Page chrome ──────────────────────────────────────────────────────────
page_chrome(title="Spend & Budget", category="SPEND")
filters = get_global_filters()


# ── Data layer with try/except fallback ──────────────────────────────────
try:
    from src.data.spend_queries import (
        get_budget_overview,
        get_channel_spend_breakdown,
        get_market_allocation,
    )
    _budget_raw = get_budget_overview(filters)
    _channel_raw = get_channel_spend_breakdown(filters)
except Exception:
    _budget_raw = None
    _channel_raw = None


# ── Fallback / mock data ────────────────────────────────────────────────

def _fmt_currency(val: float) -> str:
    if abs(val) >= 1_000_000:
        return f"${val / 1_000_000:.1f}M"
    if abs(val) >= 1_000:
        return f"${val / 1_000:.0f}K"
    return f"${val:,.0f}"


# Budget KPI cards — map from data-layer output to design-system format
if _budget_raw and len(_budget_raw) == 4:
    _annual_budget = 39_400_000
    _spent_to_date = sum(m.get("value", 0) for m in _budget_raw if "Spend" in m.get("label", "")) or 24_600_000
    _remaining = _annual_budget - _spent_to_date
    _pct_of_plan = (_spent_to_date / _annual_budget * 100) if _annual_budget else 0
    _pace_pacing = [m for m in _budget_raw if "Pacing" in m.get("label", "")]
    _pace_val = _pace_pacing[0]["value"] / 100 if _pace_pacing else 0.96
    _pace_delta_pct = abs(round((1 - _pace_val) * 100))
    _pace_label = (
        f"{_pace_delta_pct}% under glide path" if _pace_val < 1
        else f"{_pace_delta_pct}% over glide path" if _pace_val > 1
        else "on pace"
    )
else:
    _annual_budget = 39_400_000
    _spent_to_date = 24_600_000
    _remaining = 14_800_000
    _pct_of_plan = 62.4
    _pace_val = 0.96
    _pace_delta_pct = 4
    _pace_label = "4% under glide path"

# Channel allocation data
if _channel_raw and "categories" in _channel_raw:
    _alloc_data = []
    _cats = _channel_raw["categories"]
    _actuals = _channel_raw["actual"]
    _plans = _channel_raw.get("plan", _actuals)
    _max_actual = max(_actuals) if _actuals else 1
    _colors_alloc = [
        "var(--cyan)", "var(--green)", "var(--amber)",
        "#7C8BFF", "var(--text3)", "var(--text2)",
    ]
    for i, (cat, act) in enumerate(zip(_cats, _actuals)):
        _alloc_data.append({
            "name": cat,
            "amt": _fmt_currency(act),
            "pct": int(act / _max_actual * 100) if _max_actual else 0,
            "color": _colors_alloc[i % len(_colors_alloc)],
        })
else:
    _alloc_data = [
        {"name": "SEM", "amt": "$10.3M", "pct": 42, "color": "var(--cyan)"},
        {"name": "Brand Media", "amt": "$5.9M", "pct": 24, "color": "var(--green)"},
        {"name": "Social", "amt": "$5.4M", "pct": 22, "color": "var(--amber)"},
        {"name": "Email / CRM", "amt": "$1.7M", "pct": 7, "color": "#7C8BFF"},
        {"name": "Other", "amt": "$1.3M", "pct": 5, "color": "var(--text3)"},
    ]

# Reallocation ledger mock data
_realloc_rows = [
    {"move": "Social &rarr; SEM &middot; DMA 602", "why": "Below saturation", "delta": "+$420K", "roas": "+0.3&times;", "status": "APPLIED", "status_color": "var(--green)", "status_bg": "rgba(79,216,155,.14)"},
    {"move": "Display &rarr; Brand &middot; Nat'l", "why": "Share defense", "delta": "+$210K", "roas": "+0.2&times;", "status": "APPLIED", "status_color": "var(--green)", "status_bg": "rgba(79,216,155,.14)"},
    {"move": "Meta Adv+ &rarr; Email", "why": "Fatigue detected", "delta": "+$86K", "roas": "+0.4&times;", "status": "PENDING", "status_color": "var(--amber)", "status_bg": "rgba(242,177,76,.14)"},
    {"move": "SEM nb &rarr; SEM brand", "why": "Intent quality", "delta": "+$140K", "roas": "+0.1&times;", "status": "APPLIED", "status_color": "var(--green)", "status_bg": "rgba(79,216,155,.14)"},
    {"move": "Affiliate &rarr; Social", "why": "CPL ceiling hit", "delta": "+$55K", "roas": "+0.2&times;", "status": "REVIEW", "status_color": "var(--text2)", "status_bg": "var(--panel2)"},
]


# ── Build allocation bars HTML ──────────────────────────────────────────
def _build_alloc_bars() -> str:
    rows = ""
    for a in _alloc_data:
        rows += f"""
        <div style="margin-bottom:13px;">
          <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:5px;">
            <span style="font-weight:500;">{a['name']}</span>
            <span style="font-family:'JetBrains Mono',monospace;color:var(--text2);">{a['amt']}</span>
          </div>
          <div style="height:7px;border-radius:5px;background:var(--line);overflow:hidden;">
            <div style="width:{a['pct']}%;height:100%;border-radius:5px;background:{a['color']};"></div>
          </div>
        </div>"""
    return rows


# ── Build reallocation ledger rows HTML ─────────────────────────────────
def _build_realloc_rows() -> str:
    rows = ""
    for r in _realloc_rows:
        rows += f"""
        <div style="display:grid;grid-template-columns:1.4fr 1fr 1fr 96px 90px;gap:8px;align-items:center;padding:12px 18px;border-bottom:1px solid var(--line);">
          <span style="font-size:12.5px;font-weight:500;">{r['move']}</span>
          <span style="font-size:11.5px;color:var(--text2);">{r['why']}</span>
          <span style="font-family:'JetBrains Mono',monospace;font-size:12px;text-align:right;">{r['delta']}</span>
          <span style="font-family:'JetBrains Mono',monospace;font-size:12px;text-align:right;color:var(--green);">{r['roas']}</span>
          <span style="justify-self:end;text-align:center;font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:.06em;padding:3px 8px;border-radius:6px;color:{r['status_color']};background:{r['status_bg']};">{r['status']}</span>
        </div>"""
    return rows


# ── Render ──────────────────────────────────────────────────────────────

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
@keyframes rise {{ from {{ opacity:0; transform:translateY(10px); }} to {{ opacity:1; transform:translateY(0); }} }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation:none !important; transition:none !important; }} }}
</style>

<div style="display:flex;flex-direction:column;gap:16px;animation:rise .4s ease-out both;font-family:'Space Grotesk',system-ui,sans-serif;color:var(--text);">

  <!-- ═══ 4 Budget KPI Cards ═══ -->
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;">

    <!-- ANNUAL BUDGET -->
    <div style="padding:16px 18px;border-radius:14px;border:1px solid var(--line);background:var(--panel);">
      <div style="font-family:'JetBrains Mono',monospace;font-size:9.5px;letter-spacing:.12em;color:var(--text3);">ANNUAL BUDGET</div>
      <div style="font-size:26px;font-weight:600;margin-top:6px;font-family:'JetBrains Mono',monospace;font-variant-numeric:tabular-nums;">{_fmt_currency(_annual_budget)}</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text2);margin-top:3px;">FY26 committed plan</div>
    </div>

    <!-- SPENT TO DATE -->
    <div style="padding:16px 18px;border-radius:14px;border:1px solid var(--line);background:var(--panel);">
      <div style="font-family:'JetBrains Mono',monospace;font-size:9.5px;letter-spacing:.12em;color:var(--text3);">SPENT TO DATE</div>
      <div style="font-size:26px;font-weight:600;margin-top:6px;font-family:'JetBrains Mono',monospace;font-variant-numeric:tabular-nums;">{_fmt_currency(_spent_to_date)}</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--cyan);margin-top:3px;">{_pct_of_plan:.1f}% of plan</div>
    </div>

    <!-- REMAINING -->
    <div style="padding:16px 18px;border-radius:14px;border:1px solid var(--line);background:var(--panel);">
      <div style="font-family:'JetBrains Mono',monospace;font-size:9.5px;letter-spacing:.12em;color:var(--text3);">REMAINING</div>
      <div style="font-size:26px;font-weight:600;margin-top:6px;font-family:'JetBrains Mono',monospace;font-variant-numeric:tabular-nums;">{_fmt_currency(_remaining)}</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text2);margin-top:3px;">across 4 weeks left</div>
    </div>

    <!-- PACE INDEX (cyan border + radial gradient) -->
    <div style="padding:16px 18px;border-radius:14px;border:1px solid rgba(52,225,212,.28);background:radial-gradient(130% 100% at 100% 0%, rgba(52,225,212,.1), var(--panel) 60%);">
      <div style="font-family:'JetBrains Mono',monospace;font-size:9.5px;letter-spacing:.12em;color:var(--cyan);">PACE INDEX</div>
      <div style="font-size:26px;font-weight:600;margin-top:6px;font-family:'JetBrains Mono',monospace;font-variant-numeric:tabular-nums;">{_pace_val:.2f}<span style="font-size:14px;color:var(--text2);">&times;</span></div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--amber);margin-top:3px;">{_pace_label}</div>
    </div>
  </div>

  <!-- ═══ Budget Pacing + Channel Allocation ═══ -->
  <div style="display:grid;grid-template-columns:1.6fr 1fr;gap:16px;">

    <!-- Budget Pacing chart -->
    <section style="border-radius:14px;border:1px solid var(--line);background:var(--panel);padding:18px;">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
        <div style="display:flex;align-items:center;gap:10px;">
          <div style="width:3px;height:15px;background:var(--cyan);border-radius:3px;"></div>
          <span style="font-size:14px;font-weight:600;">Budget Pacing</span>
        </div>
        <span style="font-family:'JetBrains Mono',monospace;font-size:9.5px;letter-spacing:.1em;color:var(--text3);">CUMULATIVE &middot; PLAN vs ACTUAL</span>
      </div>
      <svg viewBox="0 0 560 220" width="100%" height="220" preserveAspectRatio="none" style="margin-top:8px;">
        <defs>
          <linearGradient id="spendfill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="var(--cyan)" stop-opacity="0.28"></stop>
            <stop offset="1" stop-color="var(--cyan)" stop-opacity="0"></stop>
          </linearGradient>
        </defs>
        <line x1="0" y1="55" x2="560" y2="55" stroke="var(--line)" stroke-width="1"></line>
        <line x1="0" y1="110" x2="560" y2="110" stroke="var(--line)" stroke-width="1"></line>
        <line x1="0" y1="165" x2="560" y2="165" stroke="var(--line)" stroke-width="1"></line>
        <!-- glide plan (dashed) -->
        <polyline points="0,205 51,188 102,168 153,150 204,128 255,110 306,90 357,72 408,56 459,40 510,24 560,14" fill="none" stroke="var(--text3)" stroke-width="1.6" stroke-dasharray="5 4"></polyline>
        <!-- actual spend fill -->
        <path d="M0,205 51,190 102,176 153,160 204,142 255,126 306,108 357,92 408,80 459,68 510,58 560,52 L560,220 L0,220 Z" fill="url(#spendfill)"></path>
        <!-- actual spend line (cyan) -->
        <polyline points="0,205 51,190 102,176 153,160 204,142 255,126 306,108 357,92 408,80 459,68 510,58 560,52" fill="none" stroke="var(--cyan)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"></polyline>
      </svg>
      <div style="display:flex;gap:18px;margin-top:10px;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text2);">
        <span style="display:flex;align-items:center;gap:6px;"><span style="width:14px;height:2px;background:var(--cyan);"></span>ACTUAL SPEND</span>
        <span style="display:flex;align-items:center;gap:6px;"><span style="width:14px;border-top:2px dashed var(--text3);"></span>GLIDE PLAN</span>
      </div>
    </section>

    <!-- Channel Allocation -->
    <section style="border-radius:14px;border:1px solid var(--line);background:var(--panel);padding:18px;">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">
        <div style="width:3px;height:15px;background:var(--cyan);border-radius:3px;"></div>
        <span style="font-size:14px;font-weight:600;">Channel Allocation</span>
      </div>
      {_build_alloc_bars()}
    </section>
  </div>

  <!-- ═══ Next-Best-Dollar Reallocation Ledger ═══ -->
  <section style="border-radius:14px;border:1px solid var(--line);background:var(--panel);overflow:hidden;">
    <!-- Header -->
    <div style="display:flex;align-items:center;justify-content:space-between;padding:15px 18px;border-bottom:1px solid var(--line);">
      <div style="display:flex;align-items:center;gap:10px;">
        <div style="width:3px;height:15px;background:var(--cyan);border-radius:3px;"></div>
        <span style="font-size:14px;font-weight:600;">Next-Best-Dollar Reallocation Ledger</span>
      </div>
      <span style="font-family:'JetBrains Mono',monospace;font-size:9.5px;letter-spacing:.1em;color:var(--text3);">LAST 7 DIRECTIVES</span>
    </div>
    <!-- Column headers -->
    <div style="display:grid;grid-template-columns:1.4fr 1fr 1fr 96px 90px;gap:8px;padding:9px 18px;border-bottom:1px solid var(--line);font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:.1em;color:var(--text3);">
      <span>FROM &rarr; TO</span>
      <span>RATIONALE</span>
      <span style="text-align:right;">DELTA</span>
      <span style="text-align:right;">&Delta; ROAS</span>
      <span style="text-align:right;">STATUS</span>
    </div>
    <!-- Rows -->
    {_build_realloc_rows()}
  </section>

</div>
""", unsafe_allow_html=True)


# ── Chat drawer ─────────────────────────────────────────────────────────
render_chat_drawer(page_key="spend_alloc")
