"""
App Chrome — Shared UX shell components (Signal Deck spec)
----------------------------------------------------------
Three persistent elements rendered on every page:
  1. Sidebar branding + 2-letter icon tiles  (rendered in sidebar user content)
  2. Context bar (page title, sync status, client switcher, BD/CLIENT toggle)
  3. Agent console footer (directive input, tool chips, send button)

All visual styling is injected once via CSS; the Python functions render
the minimal HTML/Streamlit widgets needed.
"""

from __future__ import annotations

import streamlit as st
from src.config.brand import (
    COLORS, COLORS_LIGHT, TYPOGRAPHY, BORDER_RADIUS, MOTION, GRADIENTS,
    get_active_colors,
)

# ---------------------------------------------------------------------------
# Nav tile codes — position-matched to PAGES in settings.py
# ---------------------------------------------------------------------------
_NAV_TILES = [
    ("SC", "Scorecard"),
    ("SP", "Spend"),
    ("MD", "Media"),        # Brand Media
    ("PM", "Perf Media"),   # Performance Media
    ("SE", "SEO"),
    ("AE", "AEO"),
    ("FN", "Funnel"),
    ("PR", "Product"),
    ("OP", "Operations"),
    ("RT", "Retention"),
    ("BA", "Awareness"),    # Brand Awareness
    ("ST", "Settings"),
]

# Badge counts (simulated — in production this comes from BFF)
_NAV_BADGES: dict[str, int] = {"OP": 3}

# ---------------------------------------------------------------------------
# CSS for the shared chrome
# ---------------------------------------------------------------------------


def _chrome_css() -> str:
    """Generate CSS for sidebar icon tiles, context bar, and agent console."""
    C = get_active_colors()
    is_dark = C is COLORS
    ff = TYPOGRAPHY["font_family"]
    mono = TYPOGRAPHY["mono_font"]
    primary = C["primary"]
    bg = C["background"]
    surface = C["surface"]
    raised = C.get("surface_raised", C.get("navy_raised", "#151B26"))
    text_p = C.get("text_primary", "#FFFFFF")
    text_s = C.get("text_secondary", "#969FB2")
    text_m = C.get("text_muted", "#586173")
    glass_border = C.get("glass_border", "rgba(255,255,255,0.07)")
    success = C.get("success", "#4FD89B")
    error = C.get("error", "#FF5C72")

    # Tile colors
    tile_bg = "rgba(255,255,255,0.06)" if is_dark else "rgba(0,0,0,0.06)"
    tile_text = text_s
    tile_active_bg = primary
    tile_active_text = "#06080C" if is_dark else "#FFFFFF"

    t_fast = MOTION["duration_fast"]
    ease = MOTION["ease_out"]

    # Build per-tile ::before rules + custom label replacement
    tile_rules = ""
    for i, (code, label) in enumerate(_NAV_TILES):
        n = i + 1  # 1-indexed nth-child
        tile_rules += f"""
  [data-testid="stSidebarNav"] ul li:nth-child({n}) [data-testid="stSidebarNavLink"] > span {{
    width: 30px !important;
    height: 30px !important;
    min-width: 30px !important;
    background: {tile_bg} !important;
    border-radius: 8px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    position: relative !important;
  }}
  [data-testid="stSidebarNav"] ul li:nth-child({n}) [data-testid="stSidebarNavLink"] > span [data-testid="stIconMaterial"] {{
    font-size: 0 !important;
    width: 30px !important;
    height: 30px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    color: transparent !important;
  }}
  [data-testid="stSidebarNav"] ul li:nth-child({n}) [data-testid="stSidebarNavLink"] > span [data-testid="stIconMaterial"]::before {{
    content: "{code}" !important;
    font-family: {mono} !important;
    font-size: 0.65rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.05em !important;
    color: {tile_text} !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 30px !important;
    height: 30px !important;
  }}
  /* Active state — teal tile */
  [data-testid="stSidebarNav"] ul li:nth-child({n}) [data-testid="stSidebarNavLink"][aria-current="page"] > span {{
    background: {tile_active_bg} !important;
    box-shadow: 0 0 16px -2px {tile_active_bg} !important;
  }}
  [data-testid="stSidebarNav"] ul li:nth-child({n}) [data-testid="stSidebarNavLink"][aria-current="page"] > span [data-testid="stIconMaterial"]::before {{
    color: {tile_active_text} !important;
  }}
  /* Hide Streamlit's default page title and replace with our short label */
  [data-testid="stSidebarNav"] ul li:nth-child({n}) [data-testid="stSidebarNavLink"] [data-testid="stMarkdownContainer"] p {{
    visibility: hidden !important;
    font-size: 0 !important;
    line-height: 0 !important;
    height: auto !important;
    width: auto !important;
  }}
  [data-testid="stSidebarNav"] ul li:nth-child({n}) [data-testid="stSidebarNavLink"] [data-testid="stMarkdownContainer"] p::after {{
    content: "{label}" !important;
    visibility: visible !important;
    font-size: 13px !important;
    line-height: 1.4 !important;
    font-family: {ff} !important;
    font-weight: 500 !important;
    color: {text_s} !important;
    letter-spacing: 0 !important;
    display: block !important;
  }}
  [data-testid="stSidebarNav"] ul li:nth-child({n}) [data-testid="stSidebarNavLink"][aria-current="page"] [data-testid="stMarkdownContainer"] p::after {{
    color: {text_p} !important;
    font-weight: 600 !important;
  }}
"""

    # Badge for Operations (nav item 9)
    badge_rules = ""
    for code, count in _NAV_BADGES.items():
        idx = next((i for i, (c, _) in enumerate(_NAV_TILES) if c == code), None)
        if idx is not None:
            n = idx + 1
            badge_rules += f"""
  [data-testid="stSidebarNav"] ul li:nth-child({n}) [data-testid="stSidebarNavLink"]::after {{
    content: "{count}" !important;
    position: absolute !important;
    right: 12px !important;
    width: 20px !important;
    height: 20px !important;
    border-radius: 50% !important;
    background: {error} !important;
    color: #FFFFFF !important;
    font-family: {mono} !important;
    font-size: 0.6rem !important;
    font-weight: 700 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
  }}
  [data-testid="stSidebarNav"] ul li:nth-child({n}) [data-testid="stSidebarNavLink"] {{
    position: relative !important;
  }}
"""

    # Context bar colors
    ctx_bg = surface if is_dark else "#FFFFFF"
    ctx_border = glass_border

    return f"""
<style>
  /* ═══════════════════════════════════════════════════════════════════════
     SIDEBAR ICON TILES — 2-letter monospace codes
     ═══════════════════════════════════════════════════════════════════════ */
{tile_rules}
{badge_rules}

  /* ── Active nav row — full-width teal highlight ───────────────────── */
  [data-testid="stSidebarNavLink"][aria-current="page"] {{
    background: rgba(52, 225, 212, 0.12) !important;
    border-left: 3px solid {primary} !important;
  }}
  section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] p {{
    color: {text_p} !important;
    font-weight: 600 !important;
  }}

  /* ── Sidebar branding block ───────────────────────────────────────── */
  .apex-sidebar-brand {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 4px 6px 16px 6px;
    margin-bottom: 0;
  }}
  .apex-sidebar-brand .apex-logo {{
    width: 26px;
    height: 26px;
    background: {primary};
    border-radius: 7px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    box-shadow: 0 0 16px -2px {primary};
  }}
  .apex-sidebar-brand .apex-logo .apex-diamond {{
    width: 9px;
    height: 9px;
    background: {"#04100F" if is_dark else "#FFFFFF"};
    border-radius: 2px;
    transform: rotate(45deg);
  }}
  .apex-sidebar-brand .apex-wordmark {{
    font-family: {mono};
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.22em;
    color: {text_p};
    white-space: nowrap;
  }}

  /* ── Collapse label at sidebar bottom ─────────────────────────────── */
  .apex-collapse-label {{
    position: fixed;
    bottom: 8px;
    left: 0;
    width: 240px;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 9px 9px;
    cursor: pointer;
    z-index: 10;
    border-radius: 9px;
    background: none;
    border: none;
    color: {text_m};
    font-family: {mono};
  }}
  .apex-collapse-label:hover {{
    color: {text_p};
  }}
  .apex-collapse-label .collapse-icon {{
    width: 30px;
    flex: none;
    text-align: center;
    font-size: 15px;
    color: inherit;
  }}
  .apex-collapse-label .collapse-text {{
    font-family: {mono} !important;
    font-size: 11px !important;
    font-weight: 400 !important;
    letter-spacing: 0.1em !important;
    color: {text_m} !important;
    white-space: nowrap;
  }}
  /* Hide collapse label when sidebar is collapsed */
  section[data-testid="stSidebar"][aria-expanded="false"] .apex-collapse-label {{
    display: none !important;
  }}

  /* Ensure Settings + nav bottom have enough room for fixed COLLAPSE label */
  [data-testid="stSidebarNav"] ul li:last-child {{
    margin-bottom: 36px !important;
  }}
  [data-testid="stSidebarNav"] ul {{
    padding-bottom: 36px !important;
  }}

  /* ═══════════════════════════════════════════════════════════════════════
     CONTEXT BAR — top bar with page title, sync, client, BD/CLIENT
     ═══════════════════════════════════════════════════════════════════════ */
  .apex-context-bar {{
    flex: none;
    height: 60px;
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 0 22px;
    border-bottom: 1px solid {glass_border};
    background: {surface};
    flex-wrap: nowrap;
  }}
  .apex-context-bar .ctx-left {{
    display: flex;
    flex-direction: column;
    min-width: 0;
  }}
  .apex-context-bar .ctx-breadcrumb {{
    font-family: {mono};
    font-size: 9.5px;
    letter-spacing: 0.2em;
    color: {text_m};
  }}
  .apex-context-bar .ctx-title {{
    font-family: {ff};
    font-size: 18px;
    font-weight: 600;
    letter-spacing: -0.01em;
    color: {text_p};
    line-height: 1.15;
  }}
  .apex-context-bar .ctx-spacer {{
    flex: 1;
  }}
  .apex-context-bar .ctx-right {{
    display: flex;
    align-items: center;
    gap: 7px;
    flex-shrink: 0;
  }}
  .apex-sync-pill {{
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 6px 11px;
    border-radius: 8px;
    border: 1px solid {glass_border};
    background: {raised};
    font-family: {mono};
    font-size: 10px;
    letter-spacing: 0.08em;
    color: {text_s};
    white-space: nowrap;
  }}
  .apex-sync-pill .sync-dot {{
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: {success};
    box-shadow: 0 0 9px {success};
    flex-shrink: 0;
  }}
  .apex-client-badge {{
    display: inline-flex;
    align-items: center;
    gap: 9px;
    padding: 6px 12px;
    border-radius: 8px;
    border: 1px solid {glass_border};
    background: {raised};
    font-family: {ff};
    color: {text_p};
    cursor: pointer;
    white-space: nowrap;
  }}
  .apex-client-badge:hover {{
    border-color: {"rgba(255,255,255,0.13)" if is_dark else "rgba(12,18,28,0.24)"};
  }}
  .apex-client-badge .client-avatar {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    background: linear-gradient(135deg, #1d4ed8, #0ea5b7);
    flex-shrink: 0;
  }}
  .apex-client-badge .client-name {{
    font-size: 12.5px;
    font-weight: 600;
    color: {text_p};
    line-height: 1.1;
  }}
  .apex-client-badge .client-sub {{
    font-family: {mono};
    font-size: 8.5px;
    letter-spacing: 0.1em;
    color: {text_m};
    line-height: 1.1;
  }}
  .apex-client-badge .client-caret {{
    color: {text_m};
    font-size: 11px;
    margin-left: 2px;
  }}
  .apex-mode-toggle {{
    display: inline-flex;
    padding: 3px;
    border-radius: 9px;
    border: 1px solid {glass_border};
    background: {raised};
    font-family: {mono};
    font-size: 10px;
    letter-spacing: 0.08em;
  }}
  .apex-mode-toggle .mode-btn {{
    padding: 5px 14px;
    cursor: pointer;
    color: {text_s};
    background: transparent;
    border: none;
    border-radius: 7px;
    transition: all {t_fast} {ease};
    white-space: nowrap;
    font-family: {mono};
    font-size: 10px;
    letter-spacing: 0.08em;
  }}
  .apex-mode-toggle .mode-btn.active {{
    background: {primary};
    color: {"#04100F" if is_dark else "#FFFFFF"};
    font-weight: 700;
  }}

  /* ── Theme toggle icon (far right of context bar) ────────────────── */
  .apex-theme-toggle-icon {{
    width: 36px;
    height: 36px;
    flex: none;
    border-radius: 9px;
    border: 1px solid {glass_border};
    background: {raised};
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    color: {text_s};
    font-size: 15px;
    flex-shrink: 0;
    transition: all {t_fast} {ease};
  }}
  .apex-theme-toggle-icon:hover {{
    color: {primary};
    border-color: {"rgba(255,255,255,0.13)" if is_dark else "rgba(12,18,28,0.24)"};
  }}

  /* ═══════════════════════════════════════════════════════════════════════
     AGENT CONSOLE — bottom command bar
     ═══════════════════════════════════════════════════════════════════════ */
  @keyframes blink {{ 0%,48% {{ opacity: 1; }} 50%,100% {{ opacity: 0; }} }}

  .apex-agent-console {{
    position: fixed;
    bottom: 0;
    left: 260px;
    width: calc(100vw - 260px);
    z-index: 998;
    flex: none;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 11px 22px;
    background: linear-gradient(180deg, {surface}, {"#0A0E14" if is_dark else "#EAEEF4"});
    border-top: 1px solid {glass_border};
    box-sizing: border-box;
  }}
  /* Adjust for collapsed sidebar */
  .stApp:has(section[data-testid="stSidebar"][aria-expanded="false"]) .apex-agent-console {{
    left: 64px;
    width: calc(100vw - 64px);
  }}
  .apex-agent-console .console-prompt {{
    font-family: {mono};
    font-size: 12px;
    color: {primary};
    font-weight: 700;
    flex-shrink: 0;
  }}
  .apex-agent-console .console-input-wrap {{
    position: relative;
    flex: 1;
    display: flex;
    align-items: center;
  }}
  .apex-agent-console .console-caret {{
    width: 2px;
    height: 15px;
    background: {primary};
    margin-right: 7px;
    flex-shrink: 0;
    animation: blink 1.1s step-end infinite;
  }}
  .apex-agent-console .console-input {{
    flex: 1;
    background: none;
    border: none;
    outline: none;
    font-family: {mono};
    font-size: 12.5px;
    color: {text_p};
    padding: 5px 0;
    min-width: 0;
  }}
  .apex-agent-console .console-input::placeholder {{
    color: {text_m};
  }}
  .apex-agent-console .tool-chips {{
    display: flex;
    gap: 7px;
    flex-shrink: 0;
  }}
  .apex-agent-console .tool-chip {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 5px 10px;
    border-radius: 7px;
    border: 1px solid {glass_border};
    background: {raised};
    font-family: {mono};
    font-size: 10px;
    color: {text_s};
    white-space: nowrap;
    flex-shrink: 0;
  }}
  .apex-agent-console .tool-chip .chip-dot {{
    width: 5px;
    height: 5px;
    border-radius: 50%;
    flex-shrink: 0;
  }}
  .apex-agent-console .tool-chip .chip-dot.dot-cyan {{
    background: {primary};
  }}
  .apex-agent-console .tool-chip .chip-dot.dot-amber {{
    background: {C.get("warning", "#F2B14C")};
  }}
  .apex-agent-console .tool-chip .chip-dot.dot-green {{
    background: {success};
  }}
  .apex-agent-console .send-btn {{
    flex: none;
    padding: 7px 16px;
    border-radius: 8px;
    background: {primary};
    color: {"#04100F" if is_dark else "#FFFFFF"};
    border: none;
    font-family: {mono};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    cursor: pointer;
    white-space: nowrap;
    flex-shrink: 0;
  }}
  .apex-agent-console .send-btn:hover {{
    filter: brightness(1.08);
  }}

  /* ── Add bottom padding to content so it doesn't hide behind console ── */
  .block-container {{
    padding-bottom: 3.5rem !important;
  }}

  /* ── Hide legacy chat drawer — replaced by agent console ──────────── */
  [data-testid="stChatInput"] {{
    display: none !important;
  }}
  /* Also hide the chat message history containers */
  [data-testid="stChatMessage"] {{
    display: none !important;
  }}

  /* ═══════════════════════════════════════════════════════════════════════
     OVERRIDE: Remove old gradient active-nav styling (replaced by subtle highlight)
     ═══════════════════════════════════════════════════════════════════════ */
  /* The old gradient active nav link is overridden by the new tile system above */

</style>
"""


# ---------------------------------------------------------------------------
# Sidebar branding (rendered in sidebar user content)
# ---------------------------------------------------------------------------

def render_sidebar_branding() -> None:
    """Render the APEX logo and wordmark in the sidebar above navigation."""
    st.markdown(
        """
        <div class="apex-sidebar-brand">
            <div class="apex-logo">
                <div class="apex-diamond"></div>
            </div>
            <span class="apex-wordmark">APEX</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Context bar (rendered at top of each page)
# ---------------------------------------------------------------------------

_CATEGORY_MAP = {
    "Executive Scorecard": "COMMAND",
    "Spend Allocation": "FINANCE",
    "Brand Media": "CHANNELS",
    "Performance Media": "CHANNELS",
    "SEO": "CHANNELS",
    "AEO": "CHANNELS",
    "Acquisition Funnel": "GROWTH",
    "Product & Experience": "DELIVERY",
    "Operations Command": "OPERATIONS",
    "Retention Forecast": "ANALYTICS",
    "Brand Awareness": "ANALYTICS",
    "Settings": "SYSTEM",
}


def render_context_bar(page_title: str, category: str | None = None) -> None:
    """Render the top context bar with page title, sync status, client, and mode toggle."""
    cat = category or _CATEGORY_MAP.get(page_title, "SYSTEM")
    mode = st.session_state.get("apex_mode", "BD Mode")
    client_name = st.session_state.get("apex_client", "Fifth Third Bank")
    is_bd = mode == "BD Mode"

    html = f"""
    <div class="apex-context-bar">
        <div class="ctx-left">
            <div class="ctx-breadcrumb">{cat} / {page_title.upper().replace("&", "&amp;")}</div>
            <div class="ctx-title">{page_title}</div>
        </div>
        <div class="ctx-spacer"></div>
        <div class="ctx-right">
            <div class="apex-sync-pill">
                <span class="sync-dot"></span>
                SYNCED &middot; 4m AGO
            </div>
            <div class="apex-client-badge">
                <div class="client-avatar"></div>
                <div style="text-align:left;line-height:1.1;">
                    <div class="client-name">{client_name}</div>
                    <div class="client-sub">+ 2 RV VALIDATION</div>
                </div>
                <span class="client-caret">&#x25BE;</span>
            </div>
            <div class="apex-mode-toggle">
                <span class="mode-btn {"active" if is_bd else ""}">BD</span>
                <span class="mode-btn {"" if is_bd else "active"}">CLIENT</span>
            </div>
            <div class="apex-theme-toggle-icon" title="Toggle theme">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
                </svg>
            </div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Agent console footer (rendered once in app.py)
# ---------------------------------------------------------------------------

def render_agent_console() -> None:
    """Render the persistent bottom agent console bar."""
    html = """
    <div class="apex-agent-console">
        <span class="console-prompt">›</span>
        <div class="console-input-wrap">
            <div class="console-caret"></div>
            <input class="console-input" type="text"
                   placeholder="ask Apex or issue a directive…  e.g. simulate +8% brand budget in DMA 602"
                   readonly />
        </div>
        <div class="tool-chips">
            <span class="tool-chip"><span class="chip-dot dot-cyan"></span>query_metrics</span>
            <span class="tool-chip"><span class="chip-dot dot-amber"></span>simulate_geo</span>
            <span class="tool-chip"><span class="chip-dot dot-green"></span>propose_action</span>
        </div>
        <button class="send-btn">SEND ↵</button>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar collapse label (bottom of sidebar)
# ---------------------------------------------------------------------------

def render_sidebar_collapse_label() -> None:
    """Render the '< COLLAPSE' label at the bottom of the sidebar."""
    st.markdown(
        """
        <div class="apex-collapse-label">
            <div class="collapse-icon">‹</div>
            <span class="collapse-text">COLLAPSE</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Inject all chrome CSS
# ---------------------------------------------------------------------------

def inject_chrome_css() -> None:
    """Inject the shared chrome CSS (call once in app.py)."""
    st.markdown(_chrome_css(), unsafe_allow_html=True)
