"""
Settings — Signal Deck spec
App configuration: Application Mode, Appearance, Data & Export,
Data Source Integrations, Benchmark Configuration.
Pure HTML/CSS via st.markdown; Streamlit widgets for interactive controls.
"""

import streamlit as st

from src.components.page_chrome import page_chrome
from src.components.filter_bar import get_global_filters
from src.components.chat_drawer import render_chat_drawer
from src.data.benchmarks.industry import STAGE_RATES, FUNNEL_STAGES, STAGE_TRANSITION_LABELS
from src.simulator.simulation_engine import ASSUMPTION_DEFAULTS, ASSUMPTION_RANGES

# ---------------------------------------------------------------------------
# Page chrome
# ---------------------------------------------------------------------------

page_chrome(title="Settings", category="SETTINGS")

# ---------------------------------------------------------------------------
# Typography constants
# ---------------------------------------------------------------------------

_mono = "'JetBrains Mono',monospace"
_ff = "'Space Grotesk',system-ui,sans-serif"

# ---------------------------------------------------------------------------
# Inject global CSS: animations, segmented controls, slider overrides
# ---------------------------------------------------------------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
@keyframes rise { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
@media (prefers-reduced-motion: reduce) { * { animation:none !important; transition:none !important; } }

/* ── Segmented pill toggles ─────────────────────────────────────── */
.stRadio[data-testid="stRadio"] > [data-testid="stWidgetLabel"] {
  display: none !important;
}
.stRadio[data-testid="stRadio"] > [role="radiogroup"] {
  display: inline-flex !important;
  flex-direction: row !important;
  gap: 4px !important;
  padding: 4px !important;
  border-radius: 10px !important;
  border: 1px solid var(--line) !important;
  background: var(--panel2) !important;
  overflow: visible !important;
}
.stRadio[data-testid="stRadio"] > [role="radiogroup"] > label {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  padding: 6px 22px !important;
  margin: 0 !important;
  border: none !important;
  background: none !important;
  color: var(--text2) !important;
  font-weight: 500 !important;
  font-size: 0.82rem !important;
  cursor: pointer !important;
  white-space: nowrap !important;
  gap: 0 !important;
  border-radius: 8px !important;
  min-height: 0 !important;
  transition: background .15s, color .15s;
}
.stRadio[data-testid="stRadio"] > [role="radiogroup"] > label > div:first-child {
  display: none !important;
}
.stRadio[data-testid="stRadio"] > [role="radiogroup"] > label:has(input:checked) {
  background: var(--cyan) !important;
  color: var(--cyanInk) !important;
  font-weight: 600 !important;
}
.stRadio[data-testid="stRadio"] > [role="radiogroup"] > label > input {
  position: absolute !important;
  opacity: 0 !important;
  width: 0 !important;
  height: 0 !important;
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# DEFAULTS — single source of truth for every tunable in the model
# ═══════════════════════════════════════════════════════════════════════════

_MEDIA_DEFAULTS = {
    "brand_cpm":            {"value": 18.0,  "min": 5.0,   "max": 60.0,  "step": 0.5,   "fmt": "$%.1f",  "label": "Brand CPM ($)",              "help": "Blended cost per 1,000 brand impressions"},
    "impression_visit_rate":{"value": 0.005, "min": 0.001, "max": 0.03,  "step": 0.001, "fmt": "%.3f",   "label": "Impression → Visit Rate",    "help": "% of brand impressions that become site visits"},
    "sem_nonbranded_share": {"value": 45.0,  "min": 10.0,  "max": 80.0,  "step": 1.0,  "fmt": "%.0f%%", "label": "SEM Non-Branded Share",      "help": "% of SEM spend allocated to non-branded terms",  "scale": 0.01},
    "default_sem_pct":      {"value": 25.0,  "min": 5.0,   "max": 60.0,  "step": 1.0,  "fmt": "%.0f%%", "label": "Default SEM % of Spend",     "help": "Fallback SEM share when no budget buckets are set", "scale": 0.01},
    "default_social_pct":   {"value": 15.0,  "min": 5.0,   "max": 50.0,  "step": 1.0,  "fmt": "%.0f%%", "label": "Default Social % of Spend",  "help": "Fallback social share when no budget buckets are set", "scale": 0.01},
}

_EFFICIENCY_DEFAULTS = {
    "brand_media":     {"value": 0.6, "label": "Brand Media",     "icon": "📺", "help": "Relative cost-efficiency of brand awareness spend at driving funded accounts"},
    "performance_sem": {"value": 1.8, "label": "Performance SEM", "icon": "🔍", "help": "Relative cost-efficiency of paid search at driving funded accounts"},
    "paid_social":     {"value": 1.1, "label": "Paid Social",     "icon": "📱", "help": "Relative cost-efficiency of paid social campaigns at driving funded accounts"},
    "seo_aeo":         {"value": 1.4, "label": "SEO / AEO",       "icon": "🌐", "help": "Relative cost-efficiency of organic search and AI engine optimization"},
    "hv_overlay":      {"value": 1.5, "label": "HV Overlay",      "icon": "🎯", "help": "Relative cost-efficiency of high-value customer overlay targeting"},
    "conversion_cro":  {"value": 2.0, "label": "Conversion / CRO","icon": "⚡", "help": "Relative cost-efficiency of conversion rate optimization efforts"},
}

_NBD_BOUNDS_DEFAULTS = {
    "brand_media":     {"min_pct": 0.05, "max_pct": 0.50},
    "performance_sem": {"min_pct": 0.10, "max_pct": 0.60},
    "paid_social":     {"min_pct": 0.05, "max_pct": 0.40},
    "seo_aeo":         {"min_pct": 0.03, "max_pct": 0.20},
    "hv_overlay":      {"min_pct": 0.02, "max_pct": 0.25},
    "conversion_cro":  {"min_pct": 0.02, "max_pct": 0.15},
}

_CONNECTORS = [
    {"name": "Google Analytics", "initials": "GA", "color": "#E37400", "desc": "Website analytics & conversion tracking"},
    {"name": "Google Ads",       "initials": "GA", "color": "#4285F4", "desc": "Search, Display, YouTube campaigns"},
    {"name": "Meta Ads",         "initials": "MT", "color": "#0668E1", "desc": "Facebook & Instagram campaigns"},
    {"name": "Snowflake",        "initials": "SF", "color": "#29B5E8", "desc": "Cloud data warehouse integration"},
    {"name": "HubSpot",          "initials": "HS", "color": "#FF7A59", "desc": "CRM pipeline & lead management"},
    {"name": "SEMrush",          "initials": "SR", "color": "#FF622D", "desc": "SEO & competitive intelligence"},
]


# ═══════════════════════════════════════════════════════════════════════════
# Initialize session state defaults
# ═══════════════════════════════════════════════════════════════════════════

if "apex_mode" not in st.session_state:
    st.session_state["apex_mode"] = "BD Mode"
if "apex_theme" not in st.session_state:
    st.session_state["apex_theme"] = "Dark"
if "apex_autopilot" not in st.session_state:
    st.session_state["apex_autopilot"] = "Assist"
if "apex_density" not in st.session_state:
    st.session_state["apex_density"] = "Comfortable"
if "apex_accent" not in st.session_state:
    st.session_state["apex_accent"] = "#34E1D4"
if "apex_export_format" not in st.session_state:
    st.session_state["apex_export_format"] = "XLSX"
if "settings_section" not in st.session_state:
    st.session_state["settings_section"] = "Mode & Appearance"

for i, label in enumerate(STAGE_TRANSITION_LABELS):
    key = f"bench_{i}"
    if key not in st.session_state:
        st.session_state[key] = STAGE_RATES[i]

for k, cfg in _MEDIA_DEFAULTS.items():
    skey = f"media_{k}"
    if skey not in st.session_state:
        st.session_state[skey] = cfg["value"]

for k, cfg in _EFFICIENCY_DEFAULTS.items():
    skey = f"eff_{k}"
    if skey not in st.session_state:
        st.session_state[skey] = cfg["value"]

for k, cfg in _NBD_BOUNDS_DEFAULTS.items():
    for bound in ("min_pct", "max_pct"):
        skey = f"nbd_{bound}_{k}"
        if skey not in st.session_state:
            st.session_state[skey] = cfg[bound]

for k, v in ASSUMPTION_DEFAULTS.items():
    skey = f"settings_{k}"
    if skey not in st.session_state:
        st.session_state[skey] = v

for conn in _CONNECTORS:
    ckey = f"connector_{conn['name'].lower().replace(' ', '_')}"
    if ckey not in st.session_state:
        st.session_state[ckey] = False


# ═══════════════════════════════════════════════════════════════════════════
# HTML helpers
# ═══════════════════════════════════════════════════════════════════════════

def _section_hdr(title: str, delay: str = "0s") -> str:
    """Signal Deck section header with cyan accent bar."""
    return (
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;'
        f'animation:rise .4s ease-out {delay} both;">'
        f'<div style="width:3px;height:15px;background:var(--cyan);border-radius:3px;"></div>'
        f'<span style="font-family:{_ff};font-size:14px;font-weight:600;color:var(--text);">{title}</span>'
        f'</div>'
    )


def _field_label(text: str) -> str:
    """Uppercase mono micro-label."""
    return (
        f'<div style="font-family:{_mono};font-size:9px;font-weight:600;'
        f'letter-spacing:.12em;text-transform:uppercase;color:var(--text3);'
        f'margin-bottom:8px;margin-top:14px;">{text}</div>'
    )


def _desc_text(text: str) -> str:
    """Description text in text2 color."""
    return (
        f'<div style="font-family:{_ff};font-size:12.5px;color:var(--text2);'
        f'line-height:1.5;margin:8px 0 4px;">{text}</div>'
    )


# ═══════════════════════════════════════════════════════════════════════════
# TOP ROW — three-column card layout
# ═══════════════════════════════════════════════════════════════════════════

col1, col2, col3 = st.columns(3)

# ── Card 1: Application Mode ─────────────────────────────────────────────
with col1:
    current_mode = st.session_state["apex_mode"]
    is_client = current_mode == "Client Mode"
    autopilot = st.session_state.get("apex_autopilot", "Assist")
    client_name = st.session_state.get("apex_client", "Fifth Third Bank")
    mode_desc = (
        f"Client view — the live {client_name} engagement."
        if is_client
        else "BD prospecting mode with industry benchmarks and scenario modeling."
    )

    st.markdown(f"""
    <div style="border-radius:14px;border:1px solid var(--line);background:var(--panel);
      padding:20px;animation:rise .4s ease-out both;">
      {_section_hdr("Application Mode")}
    </div>
    """, unsafe_allow_html=True)

    # Remove visible card wrapper, render label + radio inside Streamlit
    st.markdown(_field_label("PERSPECTIVE"), unsafe_allow_html=True)
    mode_val = st.radio("Mode", ["CLIENT", "BD"],
                        index=0 if is_client else 1,
                        horizontal=True, label_visibility="collapsed",
                        key="settings_mode_radio")
    new_mode = "Client Mode" if mode_val == "CLIENT" else "BD Mode"
    if new_mode != current_mode:
        st.session_state["apex_mode"] = new_mode
        st.rerun()

    st.markdown(_desc_text(mode_desc), unsafe_allow_html=True)

    st.markdown(_field_label("AGENT AUTOPILOT"), unsafe_allow_html=True)
    autopilot_val = st.radio("Autopilot", ["OFF", "ASSIST", "AUTO"],
                             index=["OFF", "ASSIST", "AUTO"].index(autopilot.upper()) if autopilot.upper() in ["OFF", "ASSIST", "AUTO"] else 1,
                             horizontal=True, label_visibility="collapsed",
                             key="settings_autopilot_radio")
    mapped_autopilot = {"OFF": "Manual", "ASSIST": "Assist", "AUTO": "Auto"}.get(autopilot_val, "Assist")
    if mapped_autopilot != autopilot:
        st.session_state["apex_autopilot"] = mapped_autopilot
        st.rerun()

    # Close card padding
    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

# ── Card 2: Appearance ───────────────────────────────────────────────────
with col2:
    theme = st.session_state.get("apex_theme", "Dark")
    density = st.session_state.get("apex_density", "Comfortable")
    accent = st.session_state.get("apex_accent", "#34E1D4")

    st.markdown(f"""
    <div style="border-radius:14px;border:1px solid var(--line);background:var(--panel);
      padding:20px;animation:rise .4s ease-out .05s both;">
      {_section_hdr("Appearance", ".05s")}
    </div>
    """, unsafe_allow_html=True)

    st.markdown(_field_label("THEME"), unsafe_allow_html=True)
    theme_val = st.radio("Theme", ["DARK", "LIGHT"],
                         index=0 if theme == "Dark" else 1,
                         horizontal=True, label_visibility="collapsed",
                         key="settings_theme_radio")
    if theme_val != theme.upper():
        st.session_state["apex_theme"] = theme_val.capitalize()
        st.rerun()

    st.markdown(_field_label("DENSITY"), unsafe_allow_html=True)
    density_val = st.radio("Density", ["COMFORTABLE", "COMPACT"],
                           index=0 if density == "Comfortable" else 1,
                           horizontal=True, label_visibility="collapsed",
                           key="settings_density_radio")
    mapped_density = density_val.capitalize()
    if mapped_density != density:
        st.session_state["apex_density"] = mapped_density
        st.rerun()

    st.markdown(_field_label("SIGNAL ACCENT"), unsafe_allow_html=True)

    accent_options = [
        ("#34E1D4", "Teal"),
        ("#7B68EE", "Indigo"),
        ("#4FD89B", "Green"),
        ("#E5C07B", "Gold"),
        ("#FF8C69", "Coral"),
    ]

    swatches_html = '<div style="display:flex;gap:14px;align-items:center;margin-top:4px;">'
    for hex_val, name in accent_options:
        selected = hex_val == accent
        ring = (
            f"outline:2.5px solid #FFF;outline-offset:3px;box-shadow:0 0 0 1px rgba(255,255,255,.15);"
            if selected
            else ""
        )
        swatches_html += (
            f'<div style="width:32px;height:32px;border-radius:50%;background:{hex_val};'
            f'cursor:pointer;{ring}" title="{name}"></div>'
        )
    swatches_html += '</div>'
    st.markdown(swatches_html, unsafe_allow_html=True)

    # Accent selector via hidden buttons
    acc_cols = st.columns(len(accent_options))
    for idx, (hex_val, name) in enumerate(accent_options):
        with acc_cols[idx]:
            if st.button(name, key=f"accent_{name}", use_container_width=True,
                         type="secondary"):
                st.session_state["apex_accent"] = hex_val
                st.rerun()

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

# ── Card 3: Data & Export ────────────────────────────────────────────────
with col3:
    export_fmt = st.session_state.get("apex_export_format", "XLSX")

    st.markdown(f"""
    <div style="border-radius:14px;border:1px solid var(--line);background:var(--panel);
      padding:20px;animation:rise .4s ease-out .1s both;">
      {_section_hdr("Data & Export", ".1s")}
    </div>
    """, unsafe_allow_html=True)

    st.markdown(_field_label("EXPORT FORMAT"), unsafe_allow_html=True)
    export_val = st.radio("Export", ["CSV", "XLSX", "PDF"],
                          index=["CSV", "XLSX", "PDF"].index(export_fmt),
                          horizontal=True, label_visibility="collapsed",
                          key="settings_export_radio")
    if export_val != export_fmt:
        st.session_state["apex_export_format"] = export_val
        st.rerun()

    st.markdown(_field_label("DATA CACHE"), unsafe_allow_html=True)
    st.markdown(_desc_text(
        "Cache query results locally for faster dashboard loads. "
        "Clear when data freshness is critical."
    ), unsafe_allow_html=True)

    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

    # Clear cache button — styled inline
    st.markdown("""
    <style>
    div[data-testid="stButton"] > button[kind="secondary"][data-testid="stBaseButton-secondary"].cache-btn {
      background: var(--cyan) !important;
      color: var(--cyanInk) !important;
      border-radius: 10px !important;
      border: none !important;
      font-weight: 600 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    if st.button("CLEAR CACHE & RESYNC", key="clear_cache_btn", use_container_width=True):
        st.cache_data.clear()
        st.toast("Cache cleared & data resynced", icon="✓")

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# DATA SOURCE INTEGRATIONS — full-width connector card grid
# ═══════════════════════════════════════════════════════════════════════════

st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)

st.markdown(f"""
<div style="animation:rise .4s ease-out .15s both;">
  {_section_hdr("Data Source Integrations", ".15s")}
</div>
""", unsafe_allow_html=True)

# Build connector cards as HTML + Streamlit buttons
connector_cols = st.columns(3)

for idx, conn in enumerate(_CONNECTORS):
    ckey = f"connector_{conn['name'].lower().replace(' ', '_')}"
    connected = st.session_state.get(ckey, False)
    status_label = "CONNECTED" if connected else "DISCONNECTED"
    dot_color = "var(--green)" if connected else "var(--text3)"
    pill_bg = "rgba(79,216,155,.12)" if connected else "rgba(107,117,135,.08)"
    pill_text = "var(--green)" if connected else "var(--text3)"
    delay = f"{0.15 + idx * 0.04:.2f}s"

    with connector_cols[idx % 3]:
        st.markdown(f"""
        <div style="border-radius:14px;border:1px solid var(--line);background:var(--panel);
          padding:18px;margin-bottom:14px;animation:rise .4s ease-out {delay} both;">

          <!-- Header row: icon tile + name + status pill -->
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
            <div style="width:38px;height:38px;border-radius:8px;background:{conn['color']}22;
              display:flex;align-items:center;justify-content:center;flex-shrink:0;">
              <span style="font-family:{_mono};font-size:13px;font-weight:700;
                color:{conn['color']};letter-spacing:.04em;">{conn['initials']}</span>
            </div>
            <div style="flex:1;">
              <div style="font-family:{_ff};font-size:13px;font-weight:600;color:var(--text);">{conn['name']}</div>
              <div style="font-family:{_ff};font-size:11px;color:var(--text3);margin-top:2px;">{conn['desc']}</div>
            </div>
            <div style="display:flex;align-items:center;gap:5px;padding:3px 8px;
              border-radius:6px;background:{pill_bg};">
              <div style="width:5px;height:5px;border-radius:50%;background:{dot_color};"></div>
              <span style="font-family:{_mono};font-size:9px;font-weight:600;
                letter-spacing:.08em;text-transform:uppercase;color:{pill_text};">{status_label}</span>
            </div>
          </div>

          <!-- API key mask -->
          <div style="font-family:{_mono};font-size:10px;color:var(--text3);
            margin-bottom:12px;letter-spacing:.04em;">
            {"●●●●●●●●●●●● " + ckey[-4:] if connected else "No key configured"}
          </div>
        </div>
        """, unsafe_allow_html=True)

        btn_label = "Disconnect" if connected else "Connect"
        if st.button(btn_label, key=f"btn_{ckey}", use_container_width=True):
            st.session_state[ckey] = not connected
            action = "Connected to" if not connected else "Disconnected from"
            st.toast(f"{action} {conn['name']}")
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# CONNECTION SUMMARY BAR
# ═══════════════════════════════════════════════════════════════════════════

connected_count = sum(1 for c in _CONNECTORS if st.session_state.get(f"connector_{c['name'].lower().replace(' ', '_')}"))
total_count = len(_CONNECTORS)
pct = (connected_count / total_count * 100) if total_count else 0
bar_color = "var(--green)" if pct > 50 else ("var(--amber)" if pct > 0 else "var(--text3)")

st.markdown(f"""
<div style="border-radius:12px;border:1px solid var(--line);background:var(--panel);
  padding:12px 16px;margin-top:4px;animation:rise .4s ease-out .3s both;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
    <span style="font-family:{_mono};font-size:9.5px;letter-spacing:.1em;color:var(--text3);text-transform:uppercase;">
      Connection Status</span>
    <span style="font-family:{_ff};font-size:13px;font-weight:600;color:var(--text);">
      {connected_count}/{total_count} active</span>
  </div>
  <div style="height:4px;background:var(--panel2);border-radius:2px;overflow:hidden;">
    <div style="width:{pct:.0f}%;height:100%;background:{bar_color};border-radius:2px;
      transition:width .4s ease;"></div>
  </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# BENCHMARK CONFIGURATION — tabbed slider editor
# ═══════════════════════════════════════════════════════════════════════════

st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)

st.markdown(f"""
<div style="animation:rise .4s ease-out .25s both;">
  {_section_hdr("Benchmark Configuration", ".25s")}
  <div style="font-family:{_ff};font-size:12.5px;color:var(--text2);margin:-8px 0 14px 13px;">
    Every tunable in the simulation engine and metric layer. Changes take effect immediately.
  </div>
</div>
""", unsafe_allow_html=True)


# Helper: display a slider value with Signal Deck styling
_SIM_DISPLAY = {
    "annual_media_spend":   {"label": "Annual Media Spend ($)",  "fmt": "$%.0f",  "help": "Total yearly marketing budget across all channels"},
    "brand_media_pct":      {"label": "Brand Media %",           "fmt": "%.2f",   "help": "Share of total spend allocated to brand awareness campaigns"},
    "sem_cpc_nonbranded":   {"label": "SEM CPC Non-Branded ($)", "fmt": "$%.2f",  "help": "Average cost per click for non-branded search terms"},
    "social_cpl":           {"label": "Social CPL ($)",          "fmt": "$%.0f",  "help": "Average cost per lead from paid social campaigns"},
    "visit_lead_rate":      {"label": "Visit → Lead Rate",      "fmt": "%.3f",   "help": "Fraction of website visits that convert to a qualified lead"},
    "mob6_retention_rate":  {"label": "MOB6 Retention Rate",     "fmt": "%.2f",   "help": "Share of new accounts still active after 6 months on books"},
    "pfi_conversion_rate":  {"label": "PFI Conversion Rate",     "fmt": "%.2f",   "help": "Share of leads that reach primary financial institution status"},
    "base_ltv_per_hh":      {"label": "Base LTV per HH ($)",    "fmt": "$%.0f",  "help": "Estimated lifetime value per acquired household"},
}


tab_funnel, tab_efficiency, tab_media, tab_defaults, tab_nbd = st.tabs([
    "Funnel", "Efficiency", "Media", "Simulator", "NBD Bounds"
])


# ── TAB 1: Funnel Conversion Rates ────────────────────────────────────
with tab_funnel:
    _funnel_help = [
        "Share of site visits that convert to qualified leads",
        "Share of leads that meet marketing qualification criteria",
        "Share of MQLs that begin an application",
        "Share of started apps that reach submission",
        "Credit decisioning pass rate on submitted apps",
        "Share of approved applicants who complete funding",
    ]

    bench_cols = st.columns(3)
    for i, label in enumerate(STAGE_TRANSITION_LABELS):
        with bench_cols[i % 3]:
            cur_val = st.session_state.get(f"bench_{i}", STAGE_RATES[i])
            st.markdown(f"""
            <div style="border-radius:12px;border:1px solid var(--line);background:var(--panel);
              padding:14px 16px;margin-bottom:10px;">
              <div style="font-family:{_ff};font-size:12px;color:var(--text2);margin-bottom:4px;">{label}</div>
              <div style="font-family:{_mono};font-size:16px;font-weight:700;color:var(--cyan);">{cur_val:.3f}</div>
            </div>
            """, unsafe_allow_html=True)
            st.slider(
                label,
                min_value=0.01,
                max_value=1.0,
                step=0.005,
                key=f"bench_{i}",
                format="%.3f",
                help=_funnel_help[i] if i < len(_funnel_help) else "Conversion rate for this stage transition",
                label_visibility="collapsed",
            )

    # Action buttons
    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    btn_f1, btn_f2, _ = st.columns([2, 2.5, 5.5])
    with btn_f1:
        if st.button("RESET DEFAULTS", key="reset_funnel", use_container_width=True):
            for i in range(len(STAGE_TRANSITION_LABELS)):
                st.session_state[f"bench_{i}"] = STAGE_RATES[i]
            st.toast("Funnel rates reset to industry defaults")
            st.rerun()
    with btn_f2:
        if st.button("SAVE TO METRIC LAYER", key="save_funnel", use_container_width=True,
                      type="primary"):
            st.toast("Funnel rates saved to metric layer")


# ── TAB 2: Channel Efficiency Scores ──────────────────────────────────
with tab_efficiency:
    st.markdown(f"""
    <div style="border-radius:10px;border:1px solid var(--line);background:var(--panel);
      padding:10px 14px;margin-bottom:14px;">
      <span style="font-family:{_ff};font-size:12px;color:var(--text2);">
        Relative effectiveness of each channel at driving funded accounts.
        A score of 1.0 means baseline; 2.0 means twice as efficient.
      </span>
    </div>
    """, unsafe_allow_html=True)

    eff_cols = st.columns(3)
    for idx, (k, cfg) in enumerate(_EFFICIENCY_DEFAULTS.items()):
        with eff_cols[idx % 3]:
            cur_val = st.session_state.get(f"eff_{k}", cfg["value"])
            st.markdown(f"""
            <div style="border-radius:12px;border:1px solid var(--line);background:var(--panel);
              padding:14px 16px;margin-bottom:10px;">
              <div style="font-family:{_ff};font-size:12px;color:var(--text2);">{cfg['icon']} {cfg['label']}</div>
              <div style="font-family:{_mono};font-size:16px;font-weight:700;color:var(--cyan);">{cur_val:.1f}</div>
              <div style="display:flex;justify-content:space-between;margin-top:4px;">
                <span style="font-family:{_mono};font-size:9px;color:var(--text3);">0.0</span>
                <span style="font-family:{_mono};font-size:9px;color:var(--text3);">4.0</span>
              </div>
            </div>
            """, unsafe_allow_html=True)
            st.slider(
                f"{cfg['icon']} {cfg['label']}",
                min_value=0.0,
                max_value=4.0,
                step=0.1,
                key=f"eff_{k}",
                format="%.1f",
                help=cfg.get("help", f"Efficiency score for {cfg['label']}"),
                label_visibility="collapsed",
            )

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    btn_e1, btn_e2, _ = st.columns([2, 2.5, 5.5])
    with btn_e1:
        if st.button("RESET DEFAULTS", key="reset_efficiency", use_container_width=True):
            for k, cfg in _EFFICIENCY_DEFAULTS.items():
                st.session_state[f"eff_{k}"] = cfg["value"]
            st.toast("Efficiency scores reset to defaults")
            st.rerun()
    with btn_e2:
        if st.button("SAVE TO METRIC LAYER", key="save_efficiency", use_container_width=True,
                      type="primary"):
            st.toast("Efficiency scores saved to metric layer")


# ── TAB 3: Media Coefficients ─────────────────────────────────────────
with tab_media:
    mc_cols = st.columns(3)
    for idx, (k, cfg) in enumerate(_MEDIA_DEFAULTS.items()):
        with mc_cols[idx % 3]:
            cur_val = st.session_state.get(f"media_{k}", cfg["value"])
            display_val = cfg["fmt"] % cur_val
            st.markdown(f"""
            <div style="border-radius:12px;border:1px solid var(--line);background:var(--panel);
              padding:14px 16px;margin-bottom:10px;">
              <div style="font-family:{_ff};font-size:12px;color:var(--text2);">{cfg['label']}</div>
              <div style="font-family:{_mono};font-size:16px;font-weight:700;color:var(--cyan);">{display_val}</div>
              <div style="display:flex;justify-content:space-between;margin-top:4px;">
                <span style="font-family:{_mono};font-size:9px;color:var(--text3);">{cfg['fmt'] % cfg['min']}</span>
                <span style="font-family:{_mono};font-size:9px;color:var(--text3);">{cfg['fmt'] % cfg['max']}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)
            st.slider(
                cfg["label"],
                min_value=cfg["min"],
                max_value=cfg["max"],
                step=cfg["step"],
                key=f"media_{k}",
                format=cfg["fmt"],
                help=cfg["help"],
                label_visibility="collapsed",
            )

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    btn_m1, btn_m2, _ = st.columns([2, 2.5, 5.5])
    with btn_m1:
        if st.button("RESET DEFAULTS", key="reset_media", use_container_width=True):
            for k, cfg in _MEDIA_DEFAULTS.items():
                st.session_state[f"media_{k}"] = cfg["value"]
            st.toast("Media coefficients reset to defaults")
            st.rerun()
    with btn_m2:
        if st.button("SAVE TO METRIC LAYER", key="save_media", use_container_width=True,
                      type="primary"):
            st.toast("Media coefficients saved to metric layer")


# ── TAB 4: Simulator Defaults ────────────────────────────────────────
with tab_defaults:
    sd_cols = st.columns(3)
    for idx, (k, v) in enumerate(ASSUMPTION_DEFAULTS.items()):
        r = ASSUMPTION_RANGES[k]
        display = _SIM_DISPLAY.get(k, {"label": k.replace("_", " ").title(), "fmt": "%.2f"})
        with sd_cols[idx % 3]:
            cur_val = st.session_state.get(f"settings_{k}", v)
            display_val = display["fmt"] % cur_val
            st.markdown(f"""
            <div style="border-radius:12px;border:1px solid var(--line);background:var(--panel);
              padding:14px 16px;margin-bottom:10px;">
              <div style="font-family:{_ff};font-size:12px;color:var(--text2);">{display['label']}</div>
              <div style="font-family:{_mono};font-size:16px;font-weight:700;color:var(--cyan);">{display_val}</div>
              <div style="display:flex;justify-content:space-between;margin-top:4px;">
                <span style="font-family:{_mono};font-size:9px;color:var(--text3);">{display['fmt'] % r['min']}</span>
                <span style="font-family:{_mono};font-size:9px;color:var(--text3);">{display['fmt'] % r['max']}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)
            st.slider(
                display["label"],
                min_value=float(r["min"]),
                max_value=float(r["max"]),
                step=float(r["step"]),
                key=f"settings_{k}",
                format=display["fmt"],
                help=display.get("help", f"Starting value for {display['label']}"),
                label_visibility="collapsed",
            )

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    btn_s1, btn_s2, _ = st.columns([2, 2.5, 5.5])
    with btn_s1:
        if st.button("RESET DEFAULTS", key="reset_sim_defaults", use_container_width=True):
            for k, v in ASSUMPTION_DEFAULTS.items():
                st.session_state[f"settings_{k}"] = v
            st.toast("Simulator defaults reset")
            st.rerun()
    with btn_s2:
        if st.button("SAVE TO METRIC LAYER", key="save_sim_defaults", use_container_width=True,
                      type="primary"):
            st.toast("Simulator defaults saved to metric layer")


# ── TAB 5: NBD Allocation Bounds ──────────────────────────────────────
with tab_nbd:
    st.markdown(f"""
    <div style="border-radius:10px;border:1px solid var(--line);background:var(--panel);
      padding:10px 14px;margin-bottom:14px;">
      <span style="font-family:{_ff};font-size:12px;color:var(--text2);">
        Min and max percent of budget the optimizer can assign to each channel.
      </span>
    </div>
    """, unsafe_allow_html=True)

    for k, cfg in _NBD_BOUNDS_DEFAULTS.items():
        eff_cfg = _EFFICIENCY_DEFAULTS.get(k, {})
        label = eff_cfg.get("label", k.replace("_", " ").title())
        icon = eff_cfg.get("icon", "")

        cur_min = st.session_state.get(f"nbd_min_pct_{k}", cfg["min_pct"])
        cur_max = st.session_state.get(f"nbd_max_pct_{k}", cfg["max_pct"])

        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;margin:12px 0 6px;">
          <div style="width:3px;height:13px;background:var(--cyan);border-radius:3px;"></div>
          <span style="font-family:{_ff};font-size:13px;font-weight:600;color:var(--text);">{icon} {label}</span>
          <span style="font-family:{_mono};font-size:9px;letter-spacing:.08em;color:var(--text3);">
            RANGE: {cur_min*100:.0f}% — {cur_max*100:.0f}%
          </span>
        </div>
        """, unsafe_allow_html=True)

        b1, b2 = st.columns(2)
        with b1:
            st.number_input(
                f"Min % — {label}",
                min_value=0.0, max_value=1.0, step=0.01,
                key=f"nbd_min_pct_{k}",
                format="%.2f",
                label_visibility="collapsed",
            )
        with b2:
            st.number_input(
                f"Max % — {label}",
                min_value=0.0, max_value=1.0, step=0.01,
                key=f"nbd_max_pct_{k}",
                format="%.2f",
                label_visibility="collapsed",
            )

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    btn_n1, btn_n2, _ = st.columns([2, 2.5, 5.5])
    with btn_n1:
        if st.button("RESET DEFAULTS", key="reset_nbd_bounds", use_container_width=True):
            for k, cfg in _NBD_BOUNDS_DEFAULTS.items():
                st.session_state[f"nbd_min_pct_{k}"] = cfg["min_pct"]
                st.session_state[f"nbd_max_pct_{k}"] = cfg["max_pct"]
            st.toast("NBD bounds reset to defaults")
            st.rerun()
    with btn_n2:
        if st.button("SAVE TO METRIC LAYER", key="save_nbd_bounds", use_container_width=True,
                      type="primary"):
            st.toast("NBD bounds saved to metric layer")


# ═══════════════════════════════════════════════════════════════════════════
# MODE INDICATOR BAR — fixed bottom strip
# ═══════════════════════════════════════════════════════════════════════════

mode_color = "var(--cyan)" if st.session_state["apex_mode"] == "BD Mode" else "var(--green)"
mode_label = st.session_state["apex_mode"].upper()
auto_label = st.session_state.get("apex_autopilot", "Assist").upper()

st.markdown(f"""
<div style="position:fixed;bottom:0;left:0;right:0;height:34px;
  background:var(--bg);border-top:1px solid var(--line);
  display:flex;align-items:center;justify-content:center;gap:12px;z-index:100;">
  <div style="width:6px;height:6px;border-radius:50%;background:{mode_color};
    box-shadow:0 0 8px {mode_color};"></div>
  <span style="font-family:{_mono};font-size:10px;font-weight:600;
    letter-spacing:.12em;color:{mode_color};">{mode_label}</span>
  <div style="width:1px;height:12px;background:var(--line2);"></div>
  <span style="font-family:{_mono};font-size:9px;letter-spacing:.1em;
    color:var(--text3);">AUTOPILOT: {auto_label}</span>
</div>
""", unsafe_allow_html=True)

render_chat_drawer(page_key="settings")
