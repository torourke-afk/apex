"""
Settings Page
-------------
App configuration split into three sub-pages:
  1. Mode & Appearance — BD/Client mode, theme (dark/light)
  2. Connectors — data source integrations
  3. Model Configuration — funnel rates, media coefficients, sim defaults, etc.
"""

import streamlit as st

from src.components.page_chrome import page_chrome
from src.components.card_container import card_container, card_container_end
from src.config.brand import COLORS, COLORS_LIGHT, GRADIENTS, TYPOGRAPHY, BORDER_RADIUS, MOTION, get_active_colors
from src.data.benchmarks.industry import STAGE_RATES, FUNNEL_STAGES, STAGE_TRANSITION_LABELS
from src.simulator.simulation_engine import ASSUMPTION_DEFAULTS, ASSUMPTION_RANGES

page_chrome(title="Settings", breadcrumb="Pages / Settings")

ff = TYPOGRAPHY["font_family"]

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
    {"name": "Google Ads", "icon": "fab fa-google", "color": "#4285F4", "desc": "Search, Display, YouTube campaigns"},
    {"name": "Meta Ads", "icon": "fab fa-meta", "color": "#0668E1", "desc": "Facebook & Instagram campaigns"},
    {"name": "Profound", "icon": "fas fa-database", "color": "#01B574", "desc": "Financial services data enrichment"},
    {"name": "Google Analytics", "icon": "fas fa-chart-line", "color": "#E37400", "desc": "Website analytics & conversion tracking"},
    {"name": "Salesforce", "icon": "fab fa-salesforce", "color": "#00A1E0", "desc": "CRM pipeline & lead management"},
    {"name": "DuckDB", "icon": "fas fa-server", "color": "#FFC107", "desc": "Local analytical database"},
]

# ═══════════════════════════════════════════════════════════════════════════
# Initialize session state defaults
# ═══════════════════════════════════════════════════════════════════════════
if "apex_mode" not in st.session_state:
    st.session_state["apex_mode"] = "BD Mode"
if "apex_theme" not in st.session_state:
    st.session_state["apex_theme"] = "Dark"
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
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _section_header(icon: str, title: str, subtitle: str = "") -> None:
    sub = f'<span style="color:{COLORS["text_muted"]};font-size:0.7rem;margin-left:8px;">{subtitle}</span>' if subtitle else ""
    st.markdown(f'<div style="color:{COLORS["text_primary"]};font-size:0.82rem;font-weight:700;margin:0.5rem 0 0.15rem;"><span style="margin-right:6px;">{icon}</span>{title}{sub}</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# SUB-PAGE NAVIGATION — horizontal pill selector
# ═══════════════════════════════════════════════════════════════════════════

_SECTIONS = ["Mode & Appearance", "Connectors", "Model Configuration"]

# Sub-page navigation buttons
nav_cols = st.columns([2, 2, 2.5, 3.5])
for idx, sec in enumerate(_SECTIONS):
    with nav_cols[idx]:
        if st.button(sec, key=f"nav_{sec}", use_container_width=True,
                     type="primary" if st.session_state["settings_section"] == sec else "secondary"):
            st.session_state["settings_section"] = sec
            st.rerun()

_gb = COLORS["glass_border"]
st.markdown(f"<hr style='border-color:{_gb};margin:0 0 1rem 0;'/>", unsafe_allow_html=True)

current_section = st.session_state["settings_section"]


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1: Mode & Appearance
# ═══════════════════════════════════════════════════════════════════════════
if current_section == "Mode & Appearance":

    left, right = st.columns([1, 1])

    with left:
        # ── Mode Selection ──────────────────────────────────────────────
        card_container(title="Application Mode", subtitle="Controls data sources and simulator behavior across all pages")

        mode_col1, mode_col2 = st.columns(2)
        current_mode = st.session_state["apex_mode"]

        with mode_col1:
            bd_selected = current_mode == "BD Mode"
            bd_border = COLORS["secondary"] if bd_selected else COLORS["glass_border"]
            bd_bg = "rgba(0, 117, 255, 0.08)" if bd_selected else "transparent"
            bd_check = f'<span style="color:{COLORS["secondary"]};font-size:18px;position:absolute;top:12px;right:12px;">&#10003;</span>' if bd_selected else ""
            st.markdown(f'<div style="background:{bd_bg};border:2px solid {bd_border};border-radius:{BORDER_RADIUS["lg"]};padding:1.25rem;position:relative;min-height:140px;">{bd_check}<div style="font-size:24px;margin-bottom:8px;">🏢</div><div style="color:{COLORS["text_primary"]};font-weight:700;font-size:0.95rem;margin-bottom:4px;">BD Mode</div><div style="color:{COLORS["text_secondary"]};font-size:0.75rem;line-height:1.4;">For prospecting. Simulator uses industry benchmarks with full override capability.</div></div>', unsafe_allow_html=True)
            if st.button("Select BD Mode", use_container_width=True, key="btn_bd_mode",
                          type="primary" if bd_selected else "secondary"):
                st.session_state["apex_mode"] = "BD Mode"
                st.rerun()

        with mode_col2:
            cl_selected = current_mode == "Client Mode"
            cl_border = COLORS["success"] if cl_selected else COLORS["glass_border"]
            cl_bg = "rgba(1, 181, 116, 0.08)" if cl_selected else "transparent"
            cl_check = f'<span style="color:{COLORS["success"]};font-size:18px;position:absolute;top:12px;right:12px;">&#10003;</span>' if cl_selected else ""
            st.markdown(f'<div style="background:{cl_bg};border:2px solid {cl_border};border-radius:{BORDER_RADIUS["lg"]};padding:1.25rem;position:relative;min-height:140px;">{cl_check}<div style="font-size:24px;margin-bottom:8px;">📊</div><div style="color:{COLORS["text_primary"]};font-weight:700;font-size:0.95rem;margin-bottom:4px;">Client Mode</div><div style="color:{COLORS["text_secondary"]};font-size:0.75rem;line-height:1.4;">For active clients. Simulator locked to client data + configured benchmarks.</div></div>', unsafe_allow_html=True)
            if st.button("Select Client Mode", use_container_width=True, key="btn_client_mode",
                          type="primary" if cl_selected else "secondary"):
                st.session_state["apex_mode"] = "Client Mode"
                st.rerun()

        card_container_end()

    with right:
        # ── Appearance ──────────────────────────────────────────────────
        card_container(title="Appearance", subtitle="Visual theme preferences")
        t1, t2 = st.columns([6, 4])
        with t1:
            st.markdown(f'<div style="color:{COLORS["text_primary"]};font-weight:600;font-size:0.875rem;margin-bottom:2px;">Theme</div><div style="color:{COLORS["text_secondary"]};font-size:0.75rem;">Switch between dark and light mode</div>', unsafe_allow_html=True)
        with t2:
            theme_val = st.selectbox("Theme", ["Dark", "Light"],
                                      index=0 if st.session_state["apex_theme"] == "Dark" else 1,
                                      key="theme_select", label_visibility="collapsed")
            if theme_val != st.session_state["apex_theme"]:
                st.session_state["apex_theme"] = theme_val
                st.toast(f"Theme switched to {theme_val}", icon="🎨")
                st.rerun()

        # Theme preview swatches
        if st.session_state["apex_theme"] == "Dark":
            preview_bg, preview_card, preview_text, preview_accent = "#060B26", "#0B1437", "#FFFFFF", "#0075FF"
        else:
            preview_bg, preview_card, preview_text, preview_accent = "#F7F8FC", "#FFFFFF", "#1A202C", "#0075FF"

        st.markdown(f"""<div style="display:flex;gap:8px;margin-top:0.75rem;">
            <div style="width:48px;height:48px;border-radius:10px;background:{preview_bg};border:1px solid {COLORS['glass_border']};" title="Background"></div>
            <div style="width:48px;height:48px;border-radius:10px;background:{preview_card};border:1px solid {COLORS['glass_border']};" title="Surface"></div>
            <div style="width:48px;height:48px;border-radius:10px;background:{preview_accent};border:1px solid {COLORS['glass_border']};" title="Accent"></div>
            <div style="flex:1;display:flex;align-items:center;padding-left:8px;">
                <span style="color:{COLORS['text_secondary']};font-size:0.72rem;">{st.session_state['apex_theme']} theme active</span>
            </div>
        </div>""", unsafe_allow_html=True)

        card_container_end()

        # ── Data & Export ───────────────────────────────────────────────
        card_container(title="Data & Export", subtitle="Cache and export preferences")
        st.markdown(f'<div style="color:{COLORS["text_secondary"]};font-size:0.78rem;line-height:1.6;padding:0.25rem 0;">Data refresh interval: <strong style="color:{COLORS["text_primary"]};">15 minutes</strong><br>Export format: <strong style="color:{COLORS["text_primary"]};">CSV + PNG</strong><br>Cache: <strong style="color:{COLORS["text_primary"]};">Streamlit TTL (300s)</strong></div>', unsafe_allow_html=True)
        if st.button("Clear Cache", key="clear_cache", use_container_width=True):
            st.cache_data.clear()
            st.toast("Cache cleared", icon="🗑️")
        card_container_end()


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2: Connectors
# ═══════════════════════════════════════════════════════════════════════════
elif current_section == "Connectors":

    card_container(title="Data Source Integrations", subtitle="Connect external platforms to enable live data across all dashboard pages")

    for conn in _CONNECTORS:
        ckey = f"connector_{conn['name'].lower().replace(' ', '_')}"
        connected = st.session_state[ckey]
        status_color = COLORS["success"] if connected else COLORS["text_muted"]
        status_text = "Connected" if connected else "Not Connected"
        status_dot = f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{status_color};margin-right:6px;"></span>'

        c_left, c_right = st.columns([7, 3])
        with c_left:
            st.markdown(f'<div style="display:flex;align-items:center;gap:12px;padding:0.4rem 0;"><div style="width:36px;height:36px;border-radius:{BORDER_RADIUS["md"]};background:rgba(255,255,255,0.04);border:1px solid {COLORS["glass_border"]};display:flex;align-items:center;justify-content:center;flex-shrink:0;"><i class="{conn["icon"]}" style="color:{conn["color"]};font-size:16px;"></i></div><div><div style="color:{COLORS["text_primary"]};font-weight:600;font-size:0.85rem;">{conn["name"]}</div><div style="color:{COLORS["text_secondary"]};font-size:0.7rem;">{conn["desc"]}</div></div></div>', unsafe_allow_html=True)
        with c_right:
            btn_label = "Disconnect" if connected else "Connect"
            if st.button(btn_label, key=f"btn_{ckey}", use_container_width=True):
                st.session_state[ckey] = not connected
                action = "Connected to" if not connected else "Disconnected from"
                st.toast(f"{action} {conn['name']}", icon="🔗")
                st.rerun()
        st.markdown(f'<div style="display:flex;align-items:center;padding:0 0 0.35rem 48px;font-size:0.7rem;color:{status_color};">{status_dot}{status_text}</div>', unsafe_allow_html=True)

    card_container_end()

    # Connection summary
    connected_count = sum(1 for c in _CONNECTORS if st.session_state.get(f"connector_{c['name'].lower().replace(' ', '_')}"))
    total_count = len(_CONNECTORS)
    pct = (connected_count / total_count * 100) if total_count else 0
    bar_color = COLORS["success"] if pct > 50 else COLORS["warning"] if pct > 0 else COLORS["text_muted"]
    st.markdown(f"""<div style="background:{COLORS['glass_bg']};border:1px solid {COLORS['glass_border']};border-radius:{BORDER_RADIUS['md']};padding:0.75rem 1rem;margin-top:0.5rem;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <span style="color:{COLORS['text_secondary']};font-size:0.75rem;">Connection Status</span>
            <span style="color:{COLORS['text_primary']};font-size:0.82rem;font-weight:600;">{connected_count}/{total_count} active</span>
        </div>
        <div style="height:4px;background:{COLORS['surface_raised']};border-radius:2px;overflow:hidden;">
            <div style="width:{pct}%;height:100%;background:{bar_color};border-radius:2px;"></div>
        </div>
    </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3: Model Configuration
# ═══════════════════════════════════════════════════════════════════════════
elif current_section == "Model Configuration":

    st.markdown(f'<div style="color:{COLORS["text_secondary"]};font-size:0.78rem;margin-bottom:0.5rem;">Every tunable in the simulator and NBD optimizer. Changes take effect immediately.</div>', unsafe_allow_html=True)

    tab_funnel, tab_media, tab_defaults, tab_efficiency, tab_nbd = st.tabs([
        "Funnel Rates", "Media Coefficients", "Simulator Defaults", "Channel Efficiency", "NBD Bounds"
    ])

    # ── TAB 1: Funnel Conversion Rates ────────────────────────────────────
    with tab_funnel:
        card_container(title="Funnel Conversion Rates", subtitle="Industry benchmark rates for each stage transition · Used in waterfall calculations")
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
                st.slider(
                    label,
                    min_value=0.01,
                    max_value=1.0,
                    step=0.005,
                    key=f"bench_{i}",
                    format="%.3f",
                    help=_funnel_help[i] if i < len(_funnel_help) else "Conversion rate for this stage transition",
                )
        bc1, bc2, _ = st.columns([2, 2, 6])
        with bc1:
            if st.button("↩ Reset Funnel", key="reset_funnel", use_container_width=True):
                for i in range(len(STAGE_TRANSITION_LABELS)):
                    st.session_state[f"bench_{i}"] = STAGE_RATES[i]
                st.toast("Funnel rates reset to industry defaults", icon="↩")
                st.rerun()
        card_container_end()

    # ── TAB 2: Media Coefficients ─────────────────────────────────────────
    with tab_media:
        card_container(title="Media Coefficients", subtitle="Fixed multipliers used in the simulation engine's spend → volume calculations")
        mc_cols = st.columns(3)
        for idx, (k, cfg) in enumerate(_MEDIA_DEFAULTS.items()):
            with mc_cols[idx % 3]:
                st.slider(
                    cfg["label"],
                    min_value=cfg["min"],
                    max_value=cfg["max"],
                    step=cfg["step"],
                    key=f"media_{k}",
                    format=cfg["fmt"],
                    help=cfg["help"],
                )
        mc1, mc2, _ = st.columns([2, 2, 6])
        with mc1:
            if st.button("↩ Reset Media", key="reset_media", use_container_width=True):
                for k, cfg in _MEDIA_DEFAULTS.items():
                    st.session_state[f"media_{k}"] = cfg["value"]
                st.toast("Media coefficients reset to defaults", icon="↩")
                st.rerun()
        card_container_end()

    # ── TAB 3: Simulator Assumption Defaults ──────────────────────────────
    with tab_defaults:
        card_container(title="Simulator Defaults", subtitle="Starting values for simulator sliders · These seed the input panel when no overrides are set")

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

        sd_cols = st.columns(3)
        for idx, (k, v) in enumerate(ASSUMPTION_DEFAULTS.items()):
            r = ASSUMPTION_RANGES[k]
            display = _SIM_DISPLAY.get(k, {"label": k.replace("_", " ").title(), "fmt": "%.2f"})
            with sd_cols[idx % 3]:
                st.slider(
                    display["label"],
                    min_value=float(r["min"]),
                    max_value=float(r["max"]),
                    step=float(r["step"]),
                    key=f"settings_{k}",
                    format=display["fmt"],
                    help=display.get("help", f"Starting value for {display['label']}"),
                )
        sd1, sd2, _ = st.columns([2, 2, 6])
        with sd1:
            if st.button("↩ Reset Defaults", key="reset_sim_defaults", use_container_width=True):
                for k, v in ASSUMPTION_DEFAULTS.items():
                    st.session_state[f"settings_{k}"] = v
                st.toast("Simulator defaults reset", icon="↩")
                st.rerun()
        card_container_end()

    # ── TAB 4: Channel Efficiency Scores ──────────────────────────────────
    with tab_efficiency:
        card_container(title="Channel Efficiency Scores", subtitle="Relative effectiveness of each channel at driving funded accounts · Higher = more efficient dollar-for-dollar")

        st.markdown(f'<div style="background:{COLORS["glass_bg"]};border:1px solid {COLORS["glass_border"]};border-radius:{BORDER_RADIUS["md"]};padding:0.6rem 1rem;margin-bottom:0.75rem;"><span style="color:{COLORS["text_secondary"]};font-size:0.72rem;"><i class="fas fa-info-circle" style="color:{COLORS["accent"]};"></i>&nbsp; These scores drive both the simulator\'s channel attribution model and the NBD optimizer\'s allocation logic. A score of 1.0 means baseline; 2.0 means twice as efficient.</span></div>', unsafe_allow_html=True)

        eff_cols = st.columns(3)
        for idx, (k, cfg) in enumerate(_EFFICIENCY_DEFAULTS.items()):
            with eff_cols[idx % 3]:
                st.slider(
                    f"{cfg['icon']} {cfg['label']}",
                    min_value=0.0,
                    max_value=4.0,
                    step=0.1,
                    key=f"eff_{k}",
                    format="%.1f",
                    help=cfg.get("help", f"Efficiency score for {cfg['label']}"),
                )
        ef1, ef2, _ = st.columns([2, 2, 6])
        with ef1:
            if st.button("↩ Reset Efficiency", key="reset_efficiency", use_container_width=True):
                for k, cfg in _EFFICIENCY_DEFAULTS.items():
                    st.session_state[f"eff_{k}"] = cfg["value"]
                st.toast("Efficiency scores reset to defaults", icon="↩")
                st.rerun()
        card_container_end()

    # ── TAB 5: NBD Allocation Bounds ──────────────────────────────────────
    with tab_nbd:
        card_container(title="NBD Allocation Bounds", subtitle="Min and max % of budget the optimizer can assign to each channel")

        for k, cfg in _NBD_BOUNDS_DEFAULTS.items():
            eff_cfg = _EFFICIENCY_DEFAULTS.get(k, {})
            label = eff_cfg.get("label", k.replace("_", " ").title())
            icon = eff_cfg.get("icon", "")
            _section_header(icon, label, f"Range: {cfg['min_pct']*100:.0f}%–{cfg['max_pct']*100:.0f}% of budget")
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

        nb1, nb2, _ = st.columns([2, 2, 6])
        with nb1:
            if st.button("↩ Reset Bounds", key="reset_nbd_bounds", use_container_width=True):
                for k, cfg in _NBD_BOUNDS_DEFAULTS.items():
                    st.session_state[f"nbd_min_pct_{k}"] = cfg["min_pct"]
                    st.session_state[f"nbd_max_pct_{k}"] = cfg["max_pct"]
                st.toast("NBD bounds reset to defaults", icon="↩")
                st.rerun()
        card_container_end()


# ═══════════════════════════════════════════════════════════════════════════
# Mode indicator bar at bottom
# ═══════════════════════════════════════════════════════════════════════════
mode_color = COLORS["secondary"] if st.session_state["apex_mode"] == "BD Mode" else COLORS["success"]
mode_icon = "🏢" if st.session_state["apex_mode"] == "BD Mode" else "📊"
st.markdown(f'<div style="position:fixed;bottom:0;left:0;right:0;height:36px;background:{COLORS["surface"]};border-top:1px solid {COLORS["glass_border"]};display:flex;align-items:center;justify-content:center;gap:8px;z-index:100;font-family:{ff};"><span style="font-size:14px;">{mode_icon}</span><span style="color:{mode_color};font-size:0.75rem;font-weight:600;letter-spacing:0.04em;">{st.session_state["apex_mode"].upper()}</span><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:{mode_color};box-shadow:0 0 6px {mode_color};"></span></div>', unsafe_allow_html=True)
