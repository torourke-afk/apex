"""
Full-Funnel Simulator — Signal Deck design system
---------------------------------------------------
Interactive scenario modelling surface: left panel of sliders (budget,
channel mix) feeds a saturation-damped mix model that recomputes Funded /
CPIHH / ROAS / Net Margin live vs plan-of-record.  Right panel shows
projected outcome cards and a funded-trajectory chart.

Layout follows the reference HTML: grid-template-columns minmax(320px,400px) 1fr.
All styling uses Signal Deck CSS custom properties — no hardcoded hex.
"""

import streamlit as st
import numpy as np

from src.components.filter_bar import get_global_filters
from src.components.page_chrome import page_chrome
from src.components.chat_drawer import render_chat_drawer
from src.simulator.simulation_engine import run_simulation, ASSUMPTION_DEFAULTS, ASSUMPTION_RANGES

# ── Fonts ──────────────────────────────────────────────────────────────────
_ff = "'Space Grotesk',system-ui,sans-serif"
_mono = "'JetBrains Mono',monospace"

# ── Plan-of-record baseline (frozen snapshot for delta comparison) ───────
_PLAN_INPUTS = dict(ASSUMPTION_DEFAULTS)
_PLAN = run_simulation(_PLAN_INPUTS)


# ── Helpers ────────────────────────────────────────────────────────────────

def _fmt_currency(val: float) -> str:
    if abs(val) >= 1_000_000:
        return f"${val / 1_000_000:.1f}M"
    if abs(val) >= 1_000:
        return f"${val / 1_000:.0f}K"
    return f"${val:,.0f}"


def _fmt_number(val: float) -> str:
    return f"{val:,.0f}"


def _delta_str(current: float, plan: float, invert: bool = False) -> tuple[str, str]:
    """Return (delta_text, delta_color) comparing current to plan."""
    if plan == 0:
        return ("—", "var(--text3)")
    pct = (current - plan) / abs(plan) * 100
    sign = "+" if pct >= 0 else ""
    good = pct <= 0 if invert else pct >= 0
    color = "var(--green)" if good else "var(--red)" if abs(pct) > 10 else "var(--amber)"
    return (f"{sign}{pct:.1f}% vs plan", color)


def _build_trajectory_svg(scenario_vals: list[float], plan_vals: list[float]) -> str:
    """Build an inline SVG for the funded trajectory chart."""
    w, h = 580, 180
    pad_x, pad_y = 40, 20
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    all_vals = scenario_vals + plan_vals
    mn = min(all_vals) * 0.9
    mx = max(all_vals) * 1.1
    rng = mx - mn if mx != mn else 1

    def _pt(i: int, v: float) -> tuple[int, int]:
        x = pad_x + int(i * (w - 2 * pad_x) / (len(scenario_vals) - 1))
        y = pad_y + int((1 - (v - mn) / rng) * (h - 2 * pad_y))
        return x, y

    # Build polyline points
    scen_pts = " ".join(f"{_pt(i, v)[0]},{_pt(i, v)[1]}" for i, v in enumerate(scenario_vals))
    plan_pts = " ".join(f"{_pt(i, v)[0]},{_pt(i, v)[1]}" for i, v in enumerate(plan_vals))

    # Y-axis labels (3 ticks)
    y_ticks = ""
    for frac in [0, 0.5, 1.0]:
        val = mn + frac * rng
        y = pad_y + int((1 - frac) * (h - 2 * pad_y))
        y_ticks += f'<text x="{pad_x - 6}" y="{y + 3}" text-anchor="end" font-size="9" font-family="{_mono}" fill="var(--text3)">{_fmt_number(val)}</text>'

    # X-axis month labels
    x_labels = ""
    for i, m in enumerate(months):
        x = _pt(i, 0)[0]
        x_labels += f'<text x="{x}" y="{h - 2}" text-anchor="middle" font-size="9" font-family="{_mono}" fill="var(--text3)">{m}</text>'

    # Gradient fill under scenario line
    last_pt = _pt(len(scenario_vals) - 1, scenario_vals[-1])
    first_pt = _pt(0, scenario_vals[0])

    return f"""
    <svg viewBox="0 0 {w} {h}" width="100%" xmlns="http://www.w3.org/2000/svg" style="display:block;">
      <defs>
        <linearGradient id="scenGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="var(--cyan)" stop-opacity="0.18"/>
          <stop offset="100%" stop-color="var(--cyan)" stop-opacity="0"/>
        </linearGradient>
      </defs>
      <!-- grid lines -->
      <line x1="{pad_x}" y1="{pad_y}" x2="{pad_x}" y2="{h - pad_y}" stroke="var(--line)" stroke-width="1"/>
      <line x1="{pad_x}" y1="{h - pad_y}" x2="{w - pad_x}" y2="{h - pad_y}" stroke="var(--line)" stroke-width="1"/>
      <!-- y ticks -->
      {y_ticks}
      <!-- x labels -->
      {x_labels}
      <!-- fill under scenario -->
      <polygon points="{scen_pts} {last_pt[0]},{h - pad_y} {first_pt[0]},{h - pad_y}" fill="url(#scenGrad)"/>
      <!-- plan dashed -->
      <polyline points="{plan_pts}" fill="none" stroke="var(--text3)" stroke-width="1.5" stroke-dasharray="6,4"/>
      <!-- scenario solid -->
      <polyline points="{scen_pts}" fill="none" stroke="var(--cyan)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      <!-- endpoint dots -->
      <circle cx="{last_pt[0]}" cy="{last_pt[1]}" r="4" fill="var(--cyan)"/>
    </svg>"""


# ── Session state init ─────────────────────────────────────────────────────
_SS = "sim_"

def _init():
    for k, v in ASSUMPTION_DEFAULTS.items():
        if f"{_SS}{k}" not in st.session_state:
            st.session_state[f"{_SS}{k}"] = v
    if f"{_SS}annual_media_spend_m" not in st.session_state:
        st.session_state[f"{_SS}annual_media_spend_m"] = st.session_state.get(
            f"{_SS}annual_media_spend", 5_000_000
        ) / 1_000_000

_init()


# ── Page chrome ────────────────────────────────────────────────────────────
page_chrome(title="Simulator", category="SIMULATOR")
filters = get_global_filters()


# ── Read Settings overrides ────────────────────────────────────────────────
def _get_settings_overrides() -> dict:
    overrides = {}
    _PCT_KEYS = {"sem_nonbranded_share", "default_sem_pct", "default_social_pct"}
    for k in ("brand_cpm", "impression_visit_rate", "sem_nonbranded_share",
              "default_sem_pct", "default_social_pct"):
        val = st.session_state.get(f"media_{k}")
        if val is not None:
            overrides[k] = val * 0.01 if k in _PCT_KEYS else val
    funnel_rates = []
    for i in range(6):
        val = st.session_state.get(f"bench_{i}")
        if val is not None:
            funnel_rates.append(val)
    if len(funnel_rates) == 6:
        overrides["funnel_rates"] = funnel_rates
    eff = {}
    for ch_key in ("brand_media", "performance_sem", "paid_social",
                   "seo_aeo", "hv_overlay", "conversion_cro"):
        val = st.session_state.get(f"eff_{ch_key}")
        if val is not None:
            eff[ch_key] = val
    if eff:
        overrides["channel_efficiency"] = eff
    return overrides

_settings = _get_settings_overrides()


# ── Run simulation with current slider state ──────────────────────────────
inputs = {k: st.session_state.get(f"{_SS}{k}", v) for k, v in ASSUMPTION_DEFAULTS.items()}
inputs.update(_settings)
results = run_simulation(inputs)


# ── Compute derived values for output cards ──────────────────────────────
_funded = results["Funded Accounts"]
_cpihh = results["CPIHH"]
_roi = results["ROI"]
_net_margin = results["Portfolio LTV"] - results["Total Spend"]

# Deltas vs plan
_d_funded, _c_funded = _delta_str(_funded, _PLAN["Funded Accounts"])
_d_cpihh, _c_cpihh = _delta_str(_cpihh, _PLAN["CPIHH"], invert=True)
_d_roi, _c_roi = _delta_str(_roi, _PLAN["ROI"])
_d_margin, _c_margin = _delta_str(_net_margin, _PLAN["Portfolio LTV"] - _PLAN["Total Spend"])


# ── Trajectory data (12 months, linear ramp from 0 to annual) ───────────
_monthly_scenario = [int(_funded * (i + 1) / 12) for i in range(12)]
_monthly_plan = [int(_PLAN["Funded Accounts"] * (i + 1) / 12) for i in range(12)]


# ── Slider current values for display ───────────────────────────────────
_budget_m = st.session_state.get(f"{_SS}annual_media_spend_m", 5.0)
_brand_pct = st.session_state.get(f"{_SS}brand_media_pct", 0.40)
_sem_pct = 0.25  # derived
_social_pct = 0.15  # derived
_email_residual = max(0, 1.0 - _brand_pct - _sem_pct - _social_pct)


# ── Render ─────────────────────────────────────────────────────────────────

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
@keyframes rise {{ from {{ opacity:0; transform:translateY(10px); }} to {{ opacity:1; transform:translateY(0); }} }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation:none !important; transition:none !important; }} }}

/* Range slider styling */
div[data-testid="stSlider"] > div > div > div > div {{
  background: var(--cyan) !important;
}}
div[data-testid="stSlider"] label p {{
  font-family: {_ff} !important;
  font-size: 12px !important;
  font-weight: 500 !important;
  color: var(--text2) !important;
}}
div[data-testid="stSlider"] [data-testid="stTickBarMax"],
div[data-testid="stSlider"] [data-testid="stTickBarMin"] {{
  font-family: {_mono} !important;
}}
</style>

<div style="display:grid; grid-template-columns:minmax(320px,400px) 1fr; gap:20px;
            animation:rise .4s ease-out both; font-family:{_ff}; color:var(--text);">

  <!-- ═══ LEFT: Scenario Inputs ═══ -->
  <div style="display:flex; flex-direction:column; gap:16px;">

    <!-- Header -->
    <div style="padding:20px 22px 18px; border-radius:14px; border:1px solid var(--line);
                background:var(--panel);">
      <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
        <div style="width:3px; height:15px; background:var(--cyan); border-radius:3px;"></div>
        <span style="font-size:14px; font-weight:600;">Scenario Inputs</span>
      </div>
      <div style="font-size:11px; color:var(--text3); margin-left:13px;">
        Adjust the plan — projections recompute live
      </div>
    </div>

    <!-- Slider panel (styled container; actual sliders rendered by Streamlit below) -->
    <div id="sim-slider-panel" style="padding:18px 20px; border-radius:14px;
         border:1px solid var(--line); background:var(--panel);">

      <!-- Budget display -->
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
        <span style="font-size:12px; font-weight:500; color:var(--text2);">Budget ($M)</span>
        <span style="font-family:{_mono}; font-size:13px; color:var(--cyan); font-weight:700;">
          ${_budget_m:.1f}M
        </span>
      </div>
      <div style="height:1px; background:var(--line); margin:10px 0 14px;"></div>

      <!-- Brand % display -->
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
        <span style="font-size:12px; font-weight:500; color:var(--text2);">Brand %</span>
        <span style="font-family:{_mono}; font-size:13px; color:var(--cyan); font-weight:700;">
          {_brand_pct * 100:.0f}%
        </span>
      </div>
      <div style="height:1px; background:var(--line); margin:10px 0 14px;"></div>

      <!-- SEM % display -->
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
        <span style="font-size:12px; font-weight:500; color:var(--text2);">SEM %</span>
        <span style="font-family:{_mono}; font-size:13px; color:var(--cyan); font-weight:700;">
          {_sem_pct * 100:.0f}%
        </span>
      </div>
      <div style="height:1px; background:var(--line); margin:10px 0 14px;"></div>

      <!-- Social % display -->
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
        <span style="font-size:12px; font-weight:500; color:var(--text2);">Social %</span>
        <span style="font-family:{_mono}; font-size:13px; color:var(--cyan); font-weight:700;">
          {_social_pct * 100:.0f}%
        </span>
      </div>
      <div style="height:1px; background:var(--line); margin:10px 0 14px;"></div>

      <!-- Email / CRM residual -->
      <div style="display:flex; justify-content:space-between; align-items:center; padding:10px 0 6px;">
        <span style="font-size:11px; color:var(--text3); font-weight:500;">Email / CRM (residual)</span>
        <span style="font-family:{_mono}; font-size:12px; color:var(--text3); font-weight:500;">
          {_email_residual * 100:.0f}%
        </span>
      </div>
    </div>

  </div>
  <!-- end left -->

  <!-- ═══ RIGHT: Projected Outputs ═══ -->
  <div style="display:flex; flex-direction:column; gap:16px;">

    <!-- Projected Outcome header -->
    <div style="padding:22px 24px 20px; border-radius:14px;
                border:1px solid var(--cyan); position:relative; overflow:hidden;
                background:
                  radial-gradient(ellipse 60% 80% at 30% 20%, rgba(52,225,212,.08), transparent 60%),
                  var(--panel);">
      <div style="display:flex; align-items:center; gap:10px; margin-bottom:16px;">
        <div style="width:3px; height:15px; background:var(--cyan); border-radius:3px;"></div>
        <span style="font-size:14px; font-weight:600;">Projected Outcome</span>
      </div>

      <!-- 2x2 output card grid -->
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">

        <!-- FUNDED HH -->
        <div style="padding:14px 16px; border-radius:12px; border:1px solid var(--line);
                    background:var(--panel2);">
          <div style="font-family:{_mono}; font-size:9px; letter-spacing:.14em;
                      color:var(--text3); text-transform:uppercase; margin-bottom:6px;">FUNDED HH</div>
          <div style="font-family:{_mono}; font-size:26px; font-weight:700;
                      color:var(--text); letter-spacing:-.02em; line-height:1.1;">
            {_fmt_number(_funded)}
          </div>
          <div style="font-family:{_mono}; font-size:10px; color:{_c_funded}; margin-top:4px;">
            {_d_funded}
          </div>
        </div>

        <!-- CPIHH -->
        <div style="padding:14px 16px; border-radius:12px; border:1px solid var(--line);
                    background:var(--panel2);">
          <div style="font-family:{_mono}; font-size:9px; letter-spacing:.14em;
                      color:var(--text3); text-transform:uppercase; margin-bottom:6px;">CPIHH</div>
          <div style="font-family:{_mono}; font-size:26px; font-weight:700;
                      color:var(--text); letter-spacing:-.02em; line-height:1.1;">
            {_fmt_currency(_cpihh)}
          </div>
          <div style="font-family:{_mono}; font-size:10px; color:{_c_cpihh}; margin-top:4px;">
            {_d_cpihh}
          </div>
        </div>

        <!-- BLENDED ROAS -->
        <div style="padding:14px 16px; border-radius:12px; border:1px solid var(--line);
                    background:var(--panel2);">
          <div style="font-family:{_mono}; font-size:9px; letter-spacing:.14em;
                      color:var(--text3); text-transform:uppercase; margin-bottom:6px;">BLENDED ROAS</div>
          <div style="font-family:{_mono}; font-size:26px; font-weight:700;
                      color:var(--text); letter-spacing:-.02em; line-height:1.1;">
            {_roi:.1f}&times;
          </div>
          <div style="font-family:{_mono}; font-size:10px; color:{_c_roi}; margin-top:4px;">
            {_d_roi}
          </div>
        </div>

        <!-- NET MARGIN -->
        <div style="padding:14px 16px; border-radius:12px; border:1px solid var(--line);
                    background:var(--panel2);">
          <div style="font-family:{_mono}; font-size:9px; letter-spacing:.14em;
                      color:var(--text3); text-transform:uppercase; margin-bottom:6px;">NET MARGIN</div>
          <div style="font-family:{_mono}; font-size:26px; font-weight:700;
                      color:var(--text); letter-spacing:-.02em; line-height:1.1;">
            {_fmt_currency(_net_margin)}
          </div>
          <div style="font-family:{_mono}; font-size:10px; color:{_c_margin}; margin-top:4px;">
            {_d_margin}
          </div>
        </div>

      </div>
    </div>

    <!-- Funded Trajectory chart -->
    <div style="padding:20px 22px 16px; border-radius:14px; border:1px solid var(--line);
                background:var(--panel);">
      <div style="display:flex; align-items:center; gap:10px; margin-bottom:14px;">
        <div style="width:3px; height:15px; background:var(--cyan); border-radius:3px;"></div>
        <span style="font-size:14px; font-weight:600;">Funded Trajectory</span>
      </div>
      {_build_trajectory_svg(_monthly_scenario, _monthly_plan)}
      <!-- Legend -->
      <div style="display:flex; gap:18px; justify-content:center; margin-top:10px;">
        <div style="display:flex; align-items:center; gap:6px;">
          <div style="width:16px; height:2.5px; background:var(--cyan); border-radius:2px;"></div>
          <span style="font-family:{_mono}; font-size:9px; letter-spacing:.08em; color:var(--text2);">SCENARIO</span>
        </div>
        <div style="display:flex; align-items:center; gap:6px;">
          <div style="width:16px; height:0; border-top:2px dashed var(--text3);"></div>
          <span style="font-family:{_mono}; font-size:9px; letter-spacing:.08em; color:var(--text3);">PLAN</span>
        </div>
      </div>
    </div>

  </div>
  <!-- end right -->

</div>
""", unsafe_allow_html=True)


# ── Streamlit sliders (rendered below the HTML grid, in the left column) ──
# We use st.columns to constrain the sliders to the left portion of the page
slider_col, _ = st.columns([4, 6])

with slider_col:
    st.markdown(f"""
    <div style="padding:14px 18px; border-radius:14px; border:1px solid var(--line);
                background:var(--panel); margin-top:-8px;">
      <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">
        <div style="width:3px; height:15px; background:var(--cyan); border-radius:3px;"></div>
        <span style="font-size:14px; font-weight:600; font-family:{_ff};">Adjust Parameters</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    r = ASSUMPTION_RANGES

    st.slider("Annual Media Spend ($M)", min_value=0.5, max_value=50.0,
              step=0.5, key=f"{_SS}annual_media_spend_m", format="$%.1fM")
    st.session_state[f"{_SS}annual_media_spend"] = (
        st.session_state[f"{_SS}annual_media_spend_m"] * 1_000_000
    )

    st.slider("Brand Media %", min_value=r["brand_media_pct"]["min"],
              max_value=r["brand_media_pct"]["max"],
              step=r["brand_media_pct"]["step"], key=f"{_SS}brand_media_pct")

    st.slider("MOB6 Retention Rate", min_value=r["mob6_retention_rate"]["min"],
              max_value=r["mob6_retention_rate"]["max"],
              step=r["mob6_retention_rate"]["step"], key=f"{_SS}mob6_retention_rate")

    st.slider("Base LTV per HH ($)", min_value=r["base_ltv_per_hh"]["min"],
              max_value=r["base_ltv_per_hh"]["max"],
              step=r["base_ltv_per_hh"]["step"], key=f"{_SS}base_ltv_per_hh",
              format="$%.0f")

    with st.expander("Funnel Conversion"):
        st.slider("Visit → Lead Rate", min_value=r["visit_lead_rate"]["min"],
                  max_value=r["visit_lead_rate"]["max"],
                  step=r["visit_lead_rate"]["step"], key=f"{_SS}visit_lead_rate")
        st.slider("PFI Conversion Rate", min_value=r["pfi_conversion_rate"]["min"],
                  max_value=r["pfi_conversion_rate"]["max"],
                  step=r["pfi_conversion_rate"]["step"], key=f"{_SS}pfi_conversion_rate")

    with st.expander("Channel CPCs"):
        st.slider("SEM CPC Non-Branded ($)", min_value=r["sem_cpc_nonbranded"]["min"],
                  max_value=r["sem_cpc_nonbranded"]["max"],
                  step=r["sem_cpc_nonbranded"]["step"], key=f"{_SS}sem_cpc_nonbranded",
                  format="$%.2f")
        st.slider("Social CPL ($)", min_value=r["social_cpl"]["min"],
                  max_value=r["social_cpl"]["max"],
                  step=r["social_cpl"]["step"], key=f"{_SS}social_cpl",
                  format="$%.0f")

    # Reset button
    st.markdown(f"""
    <div style="margin-top:8px; text-align:center;">
    """, unsafe_allow_html=True)

    if st.button("↺ RESET TO PLAN OF RECORD", use_container_width=True):
        for k, v in ASSUMPTION_DEFAULTS.items():
            st.session_state[f"{_SS}{k}"] = v
        st.session_state[f"{_SS}annual_media_spend_m"] = (
            ASSUMPTION_DEFAULTS["annual_media_spend"] / 1_000_000
        )
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ── Sensitivity Analysis (full width, below the main grid) ────────────────

st.markdown(f"""
<div style="margin-top:20px; animation:rise .4s ease-out .15s both;">
  <div style="padding:20px 22px 16px; border-radius:14px; border:1px solid var(--line);
              background:var(--panel);">
    <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
      <div style="width:3px; height:15px; background:var(--cyan); border-radius:3px;"></div>
      <span style="font-size:14px; font-weight:600; font-family:{_ff};">Sensitivity Analysis</span>
    </div>
    <div style="font-size:11px; color:var(--text3); margin-left:13px;">
      Sweep a single variable across its range to see impact on Retained HH
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

sweep_var = st.selectbox("Sweep variable", list(ASSUMPTION_DEFAULTS.keys()),
                         key="sim_sweep_var")
rng_sweep = ASSUMPTION_RANGES[sweep_var]
sweep_vals = np.linspace(rng_sweep["min"], rng_sweep["max"], 12)
retained_hhs: list[int] = []
for val in sweep_vals:
    sweep_inputs = dict(inputs)
    sweep_inputs[sweep_var] = val
    sweep_inputs.update(_settings)
    retained_hhs.append(run_simulation(sweep_inputs)["Retained HH"])

# Build sensitivity SVG
_sw, _sh = 680, 160
_sp_x, _sp_y = 50, 16
_mn_s = min(retained_hhs) * 0.95
_mx_s = max(retained_hhs) * 1.05
_rng_s = _mx_s - _mn_s if _mx_s != _mn_s else 1


def _sweep_pt(i: int, v: float) -> tuple[int, int]:
    x = _sp_x + int(i * (_sw - 2 * _sp_x) / (len(sweep_vals) - 1))
    y = _sp_y + int((1 - (v - _mn_s) / _rng_s) * (_sh - 2 * _sp_y))
    return x, y


_sweep_line = " ".join(
    f"{_sweep_pt(i, v)[0]},{_sweep_pt(i, v)[1]}" for i, v in enumerate(retained_hhs)
)
_sweep_dots = "".join(
    f'<circle cx="{_sweep_pt(i, v)[0]}" cy="{_sweep_pt(i, v)[1]}" r="3.5" '
    f'fill="var(--cyan)" stroke="var(--panel)" stroke-width="1.5"/>'
    for i, v in enumerate(retained_hhs)
)

# Y-axis labels
_s_yticks = ""
for frac in [0, 0.5, 1.0]:
    val = _mn_s + frac * _rng_s
    y = _sp_y + int((1 - frac) * (_sh - 2 * _sp_y))
    _s_yticks += (
        f'<text x="{_sp_x - 6}" y="{y + 3}" text-anchor="end" '
        f'font-size="9" font-family="{_mono}" fill="var(--text3)">'
        f'{_fmt_number(val)}</text>'
    )

# X-axis labels (show 6 evenly spaced)
_s_xlabels = ""
for i in range(0, len(sweep_vals), max(1, len(sweep_vals) // 6)):
    x = _sweep_pt(i, 0)[0]
    label = f"{sweep_vals[i]:.2g}"
    _s_xlabels += (
        f'<text x="{x}" y="{_sh - 1}" text-anchor="middle" '
        f'font-size="9" font-family="{_mono}" fill="var(--text3)">{label}</text>'
    )

st.markdown(f"""
<div style="padding:16px 20px; border-radius:14px; border:1px solid var(--line);
            background:var(--panel); margin-top:8px; animation:rise .4s ease-out .2s both;">
  <svg viewBox="0 0 {_sw} {_sh}" width="100%" xmlns="http://www.w3.org/2000/svg" style="display:block;">
    <!-- axes -->
    <line x1="{_sp_x}" y1="{_sp_y}" x2="{_sp_x}" y2="{_sh - _sp_y}" stroke="var(--line)" stroke-width="1"/>
    <line x1="{_sp_x}" y1="{_sh - _sp_y}" x2="{_sw - _sp_x}" y2="{_sh - _sp_y}" stroke="var(--line)" stroke-width="1"/>
    {_s_yticks}
    {_s_xlabels}
    <!-- gradient fill -->
    <defs>
      <linearGradient id="sweepGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="var(--cyan)" stop-opacity="0.12"/>
        <stop offset="100%" stop-color="var(--cyan)" stop-opacity="0"/>
      </linearGradient>
    </defs>
    <polygon points="{_sweep_line} {_sweep_pt(len(sweep_vals)-1, 0)[0]},{_sh - _sp_y} {_sweep_pt(0, 0)[0]},{_sh - _sp_y}" fill="url(#sweepGrad)"/>
    <!-- line -->
    <polyline points="{_sweep_line}" fill="none" stroke="var(--cyan)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    <!-- dots -->
    {_sweep_dots}
  </svg>
  <div style="display:flex; justify-content:space-between; margin-top:8px; padding:0 {_sp_x}px;">
    <span style="font-family:{_mono}; font-size:9px; color:var(--text3); letter-spacing:.06em;">
      {sweep_var.replace('_', ' ').upper()}
    </span>
    <span style="font-family:{_mono}; font-size:9px; color:var(--text3); letter-spacing:.06em;">
      RETAINED HH
    </span>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Chat drawer ────────────────────────────────────────────────────────────
render_chat_drawer(page_key="simulator")
