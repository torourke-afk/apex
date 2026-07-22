"""
Apex Brand System — "Signal Deck" Edition
-----------------------------------------------
Synced to the design system in DESIGN.md / design/Apex-Design-Memo-Combined.md and the
delivered mockup design/mockups/Executive-Scorecard.dc.html.

Calm, instrument-grade marketing console. Near-black ground with a soft radial glow,
hairline borders + faint ledger grid, teal signal accent (#34E1D4 dark / #0C998D light).
Red is reserved for critical/destructive only. Fonts: Space Grotesk (UI) + JetBrains Mono
(numerals, tabular-nums). Light + dark via the apex_theme session key.

NOTE: the new Apex front end is React + Tailwind over the BFF; this module keeps the legacy
Streamlit app visually aligned to the same tokens during the transition.
"""

__all__ = [
    "COLORS",
    "COLORS_LIGHT",
    "CHART_PALETTE",
    "CHART_PALETTE_EXTENDED",
    "TYPOGRAPHY",
    "SPACING",
    "BORDER_RADIUS",
    "MOTION",
    "BRAND_COLORS",
    "GRADIENTS",
    "inject_brand_css",
    "apply_brand",
    "get_active_colors",
    "hex_rgba",
]

# ---------------------------------------------------------------------------
# Color palette — Dark Glassmorphism
# ---------------------------------------------------------------------------

# Core dark backgrounds (Signal Deck — mockup token set)
_NAVY = "#06080C"         # --bg  : deepest background
_NAVY_CARD = "#0D1118"    # --panel : card / panel surface
_NAVY_RAISED = "#151B26"  # --elev : elevated card, sidebar
_NAVY_INPUT = "#10151E"   # --panel2 : form input backgrounds

# Accent — teal signal (replaces old RVGT-red-as-accent).
# Red is now reserved for critical/destructive only.
_RED = "#FF5C72"          # --red (dark) : critical / destructive
_SCARLET = "#D4374F"      # --red (light) : critical (light theme)

# Signal accent (teal)
_BLUE = "#34E1D4"         # --cyan (dark)  : teal signal/active accent
_CYAN = "#34E1D4"         # alias — single teal accent in the system

# Text
_WHITE = "#FFFFFF"
_GRAY_100 = "#E8ECF4"     # --text  : primary text on dark
_GRAY_300 = "#969FB2"     # --text2 : secondary / muted text
_GRAY_500 = "#586173"     # --text3 : tertiary / disabled

# Semantic
_GREEN = "#4FD89B"        # --green
_YELLOW = "#F2B14C"       # --amber
_RED_SOFT = "#FF5C72"     # --red : critical

# Borders & glass (hairline lines per Signal Deck)
_BORDER = "rgba(255, 255, 255, 0.07)"      # --line
_GLASS_BG = "rgba(13, 17, 24, 0.75)"        # panel surface @ 75%
_GLASS_BORDER = "rgba(255, 255, 255, 0.07)" # --line

# ---------------------------------------------------------------------------
# Light mode palette
# ---------------------------------------------------------------------------

# Light palette (Signal Deck — mockup [data-theme="light"])
_LIGHT_BG = "#DDE2EA"          # --bg
_LIGHT_SURFACE = "#FFFFFF"     # --panel
_LIGHT_RAISED = "#F4F6FA"      # --panel2
_LIGHT_INPUT = "#FFFFFF"
_LIGHT_TEXT_PRIMARY = "#0A0E16"    # --text
_LIGHT_TEXT_SECONDARY = "#414B5C"  # --text2
_LIGHT_TEXT_MUTED = "#5C6678"      # --text3
_LIGHT_BORDER = "rgba(12, 18, 28, 0.10)"   # --line
_LIGHT_GLASS_BG = "rgba(255, 255, 255, 0.85)"
_LIGHT_GLASS_BORDER = "rgba(12, 18, 28, 0.10)"
_LIGHT_BORDER_SOLID = "#E0E4EC"
_LIGHT_TEAL = "#0B897E"         # --cyan (light) : darkened teal for AA on white

COLORS_LIGHT: dict[str, str] = {
    "primary": _LIGHT_TEAL,
    "secondary": _LIGHT_TEAL,
    "accent": _LIGHT_TEAL,
    "background": _LIGHT_BG,
    "surface": _LIGHT_SURFACE,
    "surface_raised": _LIGHT_RAISED,
    "surface_sunken": "#EDF0F7",
    "surface_overlay": "rgba(255, 255, 255, 0.92)",
    "text_primary": _LIGHT_TEXT_PRIMARY,
    "text_secondary": _LIGHT_TEXT_SECONDARY,
    "text_muted": _LIGHT_TEXT_MUTED,
    "success": _GREEN,
    "warning": "#E09E00",
    "error": _RED_SOFT,
    "border": _LIGHT_BORDER,
    "border_solid": _LIGHT_BORDER_SOLID,
    "glass_bg": _LIGHT_GLASS_BG,
    "glass_border": _LIGHT_GLASS_BORDER,
    "navy": _LIGHT_BG,
    "navy_card": _LIGHT_SURFACE,
    "navy_raised": _LIGHT_RAISED,
    "blue": _BLUE,
    "cyan": _CYAN,
    "iron": _LIGHT_TEXT_SECONDARY,
    "alloy": _LIGHT_TEXT_MUTED,
    "onyx": _LIGHT_RAISED,
    "platinum": _LIGHT_TEXT_PRIMARY,
    "mahogany": _SCARLET,
    "chart_green": _GREEN,
    "chart_green_dark": "#016B46",
    "success_bg": "rgba(1, 181, 116, 0.10)",
    "warning_bg": "rgba(224, 158, 0, 0.10)",
    "error_bg": "rgba(227, 26, 26, 0.08)",
    "warning_bg_light": "rgba(224, 158, 0, 0.06)",
    "success_bg_light": "rgba(1, 181, 116, 0.06)",
}

COLORS: dict[str, str] = {
    # Brand primaries — teal signal accent (red is critical-only, see "error")
    "primary": _BLUE,
    "secondary": _BLUE,
    "accent": _CYAN,

    # Backgrounds
    "background": _NAVY,
    "surface": _NAVY_CARD,
    "surface_raised": _NAVY_RAISED,
    "surface_sunken": "#050A22",
    "surface_overlay": "rgba(6, 11, 38, 0.85)",

    # Text
    "text_primary": _WHITE,
    "text_secondary": _GRAY_300,
    "text_muted": _GRAY_500,

    # Semantic
    "success": _GREEN,
    "warning": _YELLOW,
    "error": _RED_SOFT,

    # Structural
    "border": _BORDER,
    "border_solid": "#1A2352",

    # Glass
    "glass_bg": _GLASS_BG,
    "glass_border": _GLASS_BORDER,

    # Extended palette
    "navy": _NAVY,
    "navy_card": _NAVY_CARD,
    "navy_raised": _NAVY_RAISED,
    "blue": _BLUE,
    "cyan": _CYAN,
    "iron": _GRAY_300,
    "alloy": _GRAY_500,
    "onyx": _NAVY_RAISED,
    "platinum": _GRAY_100,
    "mahogany": _SCARLET,

    # Chart scale tokens
    "chart_green": _GREEN,
    "chart_green_dark": "#016B46",

    # Semantic tints (dark-mode versions)
    "success_bg": "rgba(1, 181, 116, 0.15)",
    "warning_bg": "rgba(255, 181, 71, 0.15)",
    "error_bg": "rgba(227, 26, 26, 0.15)",
    "warning_bg_light": "rgba(255, 181, 71, 0.10)",
    "success_bg_light": "rgba(1, 181, 116, 0.10)",
}

# Chart palette — teal-led, distinct hues (Signal Deck)
CHART_PALETTE: list[str] = [
    _BLUE,       # teal accent
    "#7C8BFF",   # periwinkle (mockup secondary series)
    _GREEN,      # positive
    _YELLOW,     # amber
    _RED,        # critical
]

CHART_PALETTE_EXTENDED: list[str] = [
    _BLUE,       # teal
    "#7C8BFF",   # periwinkle
    _GREEN,      # green
    _YELLOW,     # amber
    _RED,        # red
    "#0C998D",   # deep teal
    "#1D4ED8",   # blue
    _GRAY_300,   # neutral
]

# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------

TYPOGRAPHY: dict = {
    "font_family": "'Space Grotesk', ui-sans-serif, system-ui, 'Helvetica Neue', Arial, sans-serif",
    "heading_font": "'Space Grotesk', ui-sans-serif, system-ui, 'Helvetica Neue', Arial, sans-serif",
    "mono_font": "'JetBrains Mono', ui-monospace, 'SF Mono', monospace",
    "sizes": {
        "sm": "0.75rem",
        "md": "0.875rem",
        "lg": "1rem",
        "xl": "1.25rem",
        "xxl": "1.75rem",
    },
    "weights": {
        "regular": 400,
        "medium": 500,
        "semibold": 600,
        "bold": 700,
    },
    "line_height": {
        "tight": 1.25,
        "normal": 1.5,
        "relaxed": 1.75,
    },
}

# ---------------------------------------------------------------------------
# Spacing scale
# ---------------------------------------------------------------------------

SPACING: dict[str, str] = {
    "xxs": "0.125rem",
    "xs": "0.25rem",
    "sm": "0.5rem",
    "md": "1rem",
    "lg": "1.5rem",
    "xl": "2rem",
    "xxl": "3rem",
    "xxxl": "4rem",
}

# ---------------------------------------------------------------------------
# Border radius — larger for glassmorphism
# ---------------------------------------------------------------------------

BORDER_RADIUS: dict[str, str] = {
    "sm": "6px",
    "md": "12px",
    "lg": "16px",
    "xl": "20px",
    "full": "9999px",
}

# ---------------------------------------------------------------------------
# Motion / transition tokens
# ---------------------------------------------------------------------------

MOTION: dict[str, str] = {
    "duration_fast": "150ms",
    "duration_normal": "250ms",
    "duration_slow": "400ms",
    "ease_out": "cubic-bezier(0.0, 0.0, 0.2, 1)",
    "ease_in_out": "cubic-bezier(0.4, 0.0, 0.2, 1)",
}

# ---------------------------------------------------------------------------
# Gradient helpers
# ---------------------------------------------------------------------------

GRADIENTS = {
    # Signal Deck: teal accent + radial ground glow
    "blue_cyan": f"linear-gradient(135deg, {_BLUE} 0%, #0C998D 100%)",  # teal accent ramp
    "card_bg": "linear-gradient(127deg, rgba(13,17,24,0.94) 0%, rgba(21,27,38,0.50) 100%)",
    "sidebar": f"linear-gradient(180deg, {_NAVY_RAISED} 0%, {_NAVY} 100%)",
    "ground": "radial-gradient(120% 90% at 78% -10%, #0A0E14 0%, #06080C 60%)",  # app background glow
    "red_accent": f"linear-gradient(135deg, {_RED} 0%, {_SCARLET} 100%)",
    "success": f"linear-gradient(135deg, {_GREEN} 0%, #2BD9A0 100%)",
    "warning": f"linear-gradient(135deg, {_YELLOW} 0%, #FFD06B 100%)",
    "error": f"linear-gradient(135deg, {_RED_SOFT} 0%, {_RED} 100%)",
}

# ---------------------------------------------------------------------------
# CSS injection
# ---------------------------------------------------------------------------

def _brand_css() -> str:
    ff = TYPOGRAPHY["font_family"]
    bg = COLORS["background"]
    surface = COLORS["surface"]
    text_p = COLORS["text_primary"]
    text_s = COLORS["text_secondary"]
    primary = COLORS["primary"]
    secondary = COLORS["secondary"]
    border = COLORS["border_solid"]

    t_fast = MOTION["duration_fast"]
    t_normal = MOTION["duration_normal"]
    ease_out = MOTION["ease_out"]
    ease_in_out = MOTION["ease_in_out"]

    return f"""
<style>
  /* ── Font imports ──────────────────────────────────────────────────── */
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
  @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css');

  /* ── CSS custom properties (Signal Deck reference tokens) ──────────── */
  :root {{
    /* Legacy aliases — keep for existing components */
    --color-primary: {primary};
    --color-secondary: {secondary};
    --color-accent: {COLORS["accent"]};
    --color-background: {bg};
    --color-surface: {surface};
    --color-text-primary: {text_p};
    --color-text-secondary: {text_s};
    --color-success: {COLORS["success"]};
    --color-warning: {COLORS["warning"]};
    --color-error: {COLORS["error"]};
    --color-border: {border};
    --font-family: {ff};
    --gradient-blue: {GRADIENTS["blue_cyan"]};
    --glass-bg: {COLORS["glass_bg"]};
    --glass-border: {COLORS["glass_border"]};

    /* Signal Deck reference tokens (exact match to mockup) */
    --bg: #06080C;
    --bg2: #0A0E14;
    --panel: #0D1118;
    --panel2: #10151E;
    --elev: #151B26;
    --line: rgba(255,255,255,.07);
    --line2: rgba(255,255,255,.13);
    --text: #E8ECF4;
    --text2: #A4ADBF;
    --text3: #6B7587;
    --cyan: #34E1D4;
    --cyanInk: #04100F;
    --green: #4FD89B;
    --amber: #F2B14C;
    --red: #FF5C72;
    --dot: rgba(170,205,230,.26);
    --dotStar: rgba(190,215,235,.7);
    --headerBg: rgba(10,13,19,.55);
    --aura1: rgba(52,225,212,.13);
    --aura2: rgba(38,96,210,.14);
    --aura3: rgba(108,70,200,.10);
  }}

  /* ── Keyframe animations (Signal Deck reference) ───────────────────── */
  @keyframes ringkpi {{ from {{ opacity:1; }} }}
  @keyframes ringhero {{ from {{ opacity:1; }} }}
  @keyframes rise {{ from {{ opacity:1; }} }}
  @keyframes wirein {{ from {{ opacity:1; }} }}
  @keyframes pulseonce {{
    0%,100% {{ box-shadow:inset 0 0 0 0 rgba(255,92,114,0); }}
    35% {{ box-shadow:inset 2px 0 0 0 var(--red), 0 0 18px -4px rgba(255,92,114,.5); }}
  }}
  @keyframes blink {{
    0%,48% {{ opacity:1; }}
    50%,100% {{ opacity:0; }}
  }}
  @keyframes aura1 {{
    0% {{ transform:translate(0,0) scale(1); }}
    100% {{ transform:translate(7vw,6vh) scale(1.18); }}
  }}
  @keyframes aura2 {{
    0% {{ transform:translate(0,0) scale(1); }}
    100% {{ transform:translate(-6vw,7vh) scale(1.12); }}
  }}
  @keyframes aura3 {{
    0% {{ transform:translate(0,0) scale(1); }}
    100% {{ transform:translate(5vw,-6vh) scale(1.22); }}
  }}
  @keyframes floatA {{
    0% {{ transform:translate(0,0); }}
    100% {{ transform:translate(12px,-8px); }}
  }}
  @keyframes floatB {{
    0% {{ transform:translate(0,0); }}
    100% {{ transform:translate(-10px,6px); }}
  }}
  @keyframes floatC {{
    0% {{ transform:translate(0,0); }}
    100% {{ transform:translate(8px,10px); }}
  }}
  @keyframes floatD {{
    0% {{ transform:translate(0,0); }}
    100% {{ transform:translate(-6px,-12px); }}
  }}
  @keyframes floatE {{
    0% {{ transform:translate(0,0); }}
    100% {{ transform:translate(14px,4px); }}
  }}
  @keyframes floatF {{
    0% {{ transform:translate(0,0); }}
    100% {{ transform:translate(-8px,-6px); }}
  }}
  @keyframes twinkle {{
    0%,100% {{ opacity:.35; }}
    50% {{ opacity:.95; }}
  }}
  @keyframes shimmer {{
    0% {{ background-position: 200% 0; }}
    100% {{ background-position: -200% 0; }}
  }}

  /* ── Global resets ─────────────────────────────────────────────────── */
  html, body, [class*="css"] {{
    font-family: {ff} !important;
    color: var(--text) !important;
    background-color: var(--bg) !important;
  }}

  .stApp {{
    background: radial-gradient(120% 90% at 78% -10%, var(--bg2), var(--bg) 62%) !important;
  }}

  /* ── Main content area ─────────────────────────────────────────────── */
  .block-container {{
    max-width: 1600px;
    padding: 1.5rem 2rem;
  }}

  /* ── Headings ──────────────────────────────────────────────────────── */
  h1, h2, h3, h4, h5, h6 {{
    font-family: {ff} !important;
    color: var(--text) !important;
    font-weight: 700;
  }}
  p, span:not([data-testid="stIconMaterial"]), div, label {{
    font-family: {ff} !important;
  }}

  /* ── Sidebar — dark gradient ───────────────────────────────────────── */
  section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, var(--panel), var(--bg2)) !important;
    border-right: 1px solid var(--line) !important;
    width: 260px !important;
    min-width: 260px !important;
    overflow-x: hidden !important;
    overflow-y: auto !important;
  }}
  section[data-testid="stSidebar"] > div {{
    background: transparent !important;
    padding-top: 0.5rem !important;
  }}
  [data-testid="stSidebarHeader"] {{
    padding: 0 !important;
    min-height: 0 !important;
  }}

  /* ── Reorder sidebar: branding above nav ────────────────────────────── */
  [data-testid="stSidebarContent"] {{
    display: flex !important;
    flex-direction: column !important;
  }}
  [data-testid="stSidebarHeader"] {{
    order: 0 !important;
  }}
  [data-testid="stSidebarUserContent"] {{
    order: 1 !important;
    padding-top: 0 !important;
  }}
  [data-testid="stSidebarNav"] {{
    order: 2 !important;
  }}
  /* Remove the default separator between nav and user content */
  [data-testid="stSidebarNavSeparator"] {{
    display: none !important;
  }}

  section[data-testid="stSidebar"] .stMarkdown,
  section[data-testid="stSidebar"] label,
  section[data-testid="stSidebar"] span,
  section[data-testid="stSidebar"] p {{
    color: var(--text2) !important;
  }}
  section[data-testid="stSidebar"] h1,
  section[data-testid="stSidebar"] h2,
  section[data-testid="stSidebar"] h3 {{
    color: var(--text) !important;
  }}

  /* ── Sidebar nav items ─────────────────────────────────────────────── */
  [data-testid="stSidebarNav"] {{
    padding: 0 0.5rem !important;
    margin-top: 0 !important;
    display: flex !important;
    flex-direction: column !important;
    flex: 1 !important;
  }}
  [data-testid="stSidebarNav"] ul {{
    display: flex !important;
    flex-direction: column !important;
    flex: 1 !important;
    width: 100% !important;
    padding: 0 !important;
    margin: 0 !important;
    box-sizing: border-box !important;
  }}
  [data-testid="stSidebarNav"] ul li {{
    width: 100% !important;
    min-width: 0 !important;
    overflow: visible !important;
    box-sizing: border-box !important;
  }}
  [data-testid="stSidebarNavLink"] {{
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    gap: 0.5rem !important;
    padding: 0.5rem 0.75rem !important;
    border-radius: {BORDER_RADIUS["md"]} !important;
    margin: 2px 0 !important;
    text-decoration: none !important;
    transition: background {t_fast} {ease_out} !important;
    overflow: visible !important;
    width: 100% !important;
    min-width: 0 !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
  }}
  /* Text and icon color inside nav links */
  section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] p,
  section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] [data-testid="stIconMaterial"] {{
    color: var(--text2) !important;
    font-weight: 500;
  }}
  [data-testid="stSidebarNavLink"]:hover {{
    background: rgba(0, 117, 255, 0.08) !important;
  }}

  /* ── Nav link inner layout ─────────────────────────────────────────── */
  /* > span:first-child = icon wrapper, > span:last-child = label container */
  [data-testid="stSidebarNavLink"] > span:first-child {{
    display: inline-flex !important;
    align-items: center !important;
    flex-shrink: 0 !important;
  }}
  [data-testid="stSidebarNavLink"] > span:first-child::after {{ display: none !important; }}
  /* Label container — the second span with [label] attribute */
  [data-testid="stSidebarNavLink"] > span[label],
  [data-testid="stSidebarNavLink"] > span:last-child {{
    flex: 1 1 0% !important;
    min-width: 0 !important;
    overflow: visible !important;
    margin-left: 0 !important;
    width: auto !important;
  }}
  [data-testid="stSidebarNavLink"] > div {{
    flex: 1 1 0% !important;
    min-width: 0 !important;
    overflow: visible !important;
    margin-left: 0 !important;
  }}
  [data-testid="stSidebarNavLink"] [data-testid="stMarkdownContainer"] {{
    min-width: 0 !important;
    overflow: visible !important;
  }}
  [data-testid="stSidebarNavLink"] [data-testid="stMarkdownContainer"] p {{
    white-space: nowrap !important;
    overflow: visible !important;
    text-overflow: clip !important;
    margin: 0 !important;
    font-size: 0.85rem !important;
  }}

  /* ── Pin Settings to bottom of sidebar nav ────────────────────────────── */
  /* Push the last visible nav item (Settings) to the bottom */
  [data-testid="stSidebarNav"] ul li:last-child {{
    margin-top: auto !important;
  }}
  /* ── Active nav item — subtle teal highlight (icon tile handles icon bg) ── */
  [data-testid="stSidebarNavLink"][aria-current="page"] {{
    background: rgba(52, 225, 212, 0.10) !important;
    border-radius: {BORDER_RADIUS["md"]} !important;
    border-left: 3px solid var(--cyan) !important;
  }}
  section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] p {{
    color: var(--text) !important;
    font-weight: 600 !important;
  }}

  /* ── Collapsed sidebar — 64px icon rail ─────────────────────────────── */
  /* Only constrain the sidebar element itself; inner containers may remain at
     260px — the icon is positioned via padding-left from the left edge so
     it lands at (64-18)/2 = 23px regardless of parent container widths.    */
  section[data-testid="stSidebar"][aria-expanded="false"] {{
    width: 64px !important;
    min-width: 64px !important;
    max-width: 64px !important;
    transform: none !important;
    margin-left: 0 !important;
    display: block !important;
    visibility: visible !important;
    overflow-x: hidden !important;
  }}
  section[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarUserContent"] {{
    display: none !important;
  }}
  section[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarNav"] {{
    padding: 0 !important;
  }}
  section[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarNavLink"] [data-testid="stMarkdownContainer"] {{
    display: none !important;
  }}
  section[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarNavLink"] > div {{
    display: none !important;
  }}
  section[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarNavLink"] {{
    width: 64px !important;
    justify-content: center !important;
    padding: 0.5rem 0 !important;
    margin: 2px 0 !important;
    box-sizing: border-box !important;
  }}
  section[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarNavLink"] > span {{
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
  }}
  section[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarNavLink"][aria-current="page"] {{
    background: rgba(52, 225, 212, 0.10) !important;
  }}
  [data-testid="stExpandSidebarButton"] button {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
  }}
  /* Zero out Streamlit's hardcoded marginLeft on the nav label container */
  [data-testid="stSidebarNavLink"] .e1lpckdq20 {{
    margin-left: 0 !important;
  }}
  /* Nav-link Material icons */
  [data-testid="stSidebarNavLink"] [data-testid="stIconMaterial"] {{
    font-size: 18px !important;
    line-height: 1 !important;
    width: 18px !important;
    min-width: 18px !important;
    height: 18px !important;
    flex-shrink: 0 !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    color: inherit !important;
    overflow: hidden !important;
    margin: 0 !important;
    padding: 0 !important;
  }}

  /* Hide Material Symbols text only in the toggle buttons, replace with FA */
  [data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"],
  [data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"] {{
    font-size: 0 !important;
    line-height: 0 !important;
    overflow: hidden !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 20px !important;
    height: 20px !important;
  }}
  [data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"]::before {{
    font-family: 'Font Awesome 6 Free' !important;
    font-weight: 900 !important;
    font-size: 14px !important;
    content: "\\f0c9" !important;
    color: var(--text2) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
  }}
  /* Also fix the sidebar collapse button icon */
  [data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"]::before {{
    font-family: 'Font Awesome 6 Free' !important;
    font-weight: 900 !important;
    font-size: 12px !important;
    content: "\\f053" !important;
    color: var(--text2) !important;
  }}

  /* ── Metric cards (st.metric) ──────────────────────────────────────── */
  [data-testid="metric-container"] {{
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 1.25rem;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    transition: border-color {t_normal} {ease_in_out};
  }}
  [data-testid="metric-container"]:hover {{
    border-color: var(--line2);
  }}
  [data-testid="metric-container"] label {{
    color: var(--text3) !important;
    font-family: 'JetBrains Mono', ui-monospace, monospace !important;
    font-size: 9px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.15em;
  }}
  [data-testid="metric-container"] [data-testid="stMetricValue"] {{
    color: var(--text) !important;
    font-weight: 700;
    font-size: 30px;
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.02em;
  }}

  /* ── Primary buttons — gradient (skip filter-bar buttons) ───────────── */
  .stButton > button[kind="primary"] {{
    background: {GRADIENTS["blue_cyan"]} !important;
    color: var(--cyanInk) !important;
    border: none !important;
    font-weight: 600;
    border-radius: {BORDER_RADIUS["md"]};
    transition: all {t_fast} {ease_out};
    box-shadow: 0 2px 12px rgba(52, 225, 212, 0.3);
  }}
  :not(.filter-bar-container) > .stButton > button {{
    background: var(--panel) !important;
    color: var(--text) !important;
    border: 1px solid var(--line) !important;
    font-weight: 600;
    border-radius: {BORDER_RADIUS["md"]};
    transition: all {t_fast} {ease_out};
  }}
  :not(.filter-bar-container) > .stButton > button:hover {{
    border-color: var(--line2) !important;
    transform: translateY(-1px);
  }}

  /* ── Form inputs — dark themed ─────────────────────────────────────── */
  .stSelectbox > div > div,
  .stMultiSelect > div > div,
  .stTextInput > div > div > input,
  [data-baseweb="select"] {{
    background-color: var(--panel2) !important;
    border-color: var(--line) !important;
    color: var(--text) !important;
    border-radius: {BORDER_RADIUS["md"]} !important;
  }}
  [data-baseweb="select"] > div {{
    background-color: var(--panel2) !important;
    border-color: var(--line) !important;
    color: var(--text) !important;
  }}
  .stSelectbox label, .stMultiSelect label, .stTextInput label {{
    color: var(--text2) !important;
  }}

  /* ── Radio buttons ─────────────────────────────────────────────────── */
  .stRadio label {{
    color: var(--text2) !important;
  }}
  .stRadio [data-testid="stMarkdownContainer"] p {{
    color: var(--text2) !important;
  }}

  /* ── Toggle ────────────────────────────────────────────────────────── */
  [data-testid="stToggle"] label span {{
    color: var(--text2) !important;
  }}

  /* ── Dataframe / table ─────────────────────────────────────────────── */
  .stDataFrame {{
    border: 1px solid var(--line) !important;
    border-radius: {BORDER_RADIUS["md"]};
  }}
  .stDataFrame [data-testid="StyledDataFrameDataCell"],
  .stDataFrame td {{
    color: var(--text) !important;
    background-color: transparent !important;
    border-color: var(--line) !important;
  }}
  .stDataFrame th {{
    color: var(--text2) !important;
    background-color: var(--elev) !important;
    border-color: var(--line) !important;
  }}

  /* ── AgGrid ────────────────────────────────────────────────────────── */
  .ag-theme-streamlit {{
    --ag-background-color: var(--panel) !important;
    --ag-header-background-color: var(--elev) !important;
    --ag-odd-row-background-color: var(--panel2) !important;
    --ag-row-hover-color: rgba(52, 225, 212, 0.06) !important;
    --ag-foreground-color: var(--text) !important;
    --ag-header-foreground-color: var(--text2) !important;
    --ag-border-color: var(--line) !important;
  }}

  /* ── Tabs ──────────────────────────────────────────────────────────── */
  .stTabs [data-baseweb="tab-list"] {{
    border-bottom: 1px solid var(--line);
    background: transparent;
  }}
  .stTabs [data-baseweb="tab"] {{
    color: var(--text2) !important;
  }}
  .stTabs [data-baseweb="tab"][aria-selected="true"] {{
    color: var(--text) !important;
    border-bottom: 2px solid var(--cyan);
  }}

  /* ── Dividers ──────────────────────────────────────────────────────── */
  hr {{
    border-color: var(--line) !important;
  }}

  /* ── Plotly chart backgrounds ──────────────────────────────────────── */
  .stPlotlyChart {{
    border-radius: {BORDER_RADIUS["md"]};
  }}

  /* ── Hide Streamlit chrome (keep sidebar toggle visible) ────────────── */
  footer {{
    visibility: hidden;
  }}
  /* Hide deploy button and main menu */
  [data-testid="stAppDeployButton"] {{
    display: none !important;
  }}
  [data-testid="stMainMenu"] {{
    display: none !important;
  }}
  /* Make the header bar transparent and minimal */
  header[data-testid="stHeader"] {{
    background: var(--headerBg) !important;
  }}
  /* Style the sidebar expand button (visible when sidebar is collapsed) */
  [data-testid="stExpandSidebarButton"] {{
    color: var(--text2) !important;
  }}
  /* Hide the decoration line */
  [data-testid="stDecoration"] {{
    display: none !important;
  }}

  /* ── Global transitions ────────────────────────────────────────────── */
  .stButton > button,
  [data-testid="stSidebarNavLink"],
  .stSelectbox,
  .stMultiSelect {{
    transition: all {t_fast} {ease_out};
  }}

  /* ── Tabular nums ──────────────────────────────────────────────────── */
  .apex-metric-value {{
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.02em;
  }}

  /* ── Section headers (Signal Deck) ─────────────────────────────────── */
  .apex-section-header {{
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }}
  .apex-section-header .accent-bar {{
    width: 3px;
    height: 18px;
    border-radius: 2px;
    background: var(--cyan);
  }}
  .apex-section-header .accent-bar.critical {{
    background: var(--red);
  }}
  .apex-section-header .section-title {{
    font-size: 14px;
    font-weight: 600;
    color: var(--text);
  }}
  .apex-section-header .section-meta {{
    font-family: 'JetBrains Mono', ui-monospace, monospace;
    font-size: 10px;
    font-weight: 500;
    color: var(--text3);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-left: auto;
  }}

  /* ── Segmented controls (Signal Deck) ──────────────────────────────── */
  .apex-segmented-track {{
    background: var(--panel2);
    border-radius: 8px;
    padding: 2px;
    display: inline-flex;
    gap: 2px;
  }}
  .apex-segmented-track .segment {{
    padding: 4px 12px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 500;
    color: var(--text2);
    cursor: pointer;
    transition: all {t_fast} {ease_out};
  }}
  .apex-segmented-track .segment.active {{
    background: var(--cyan);
    color: var(--cyanInk);
  }}

  /* ── Scrollbars (reference match) ──────────────────────────────────── */
  ::-webkit-scrollbar {{ width: 9px; height: 9px; }}
  ::-webkit-scrollbar-track {{ background: transparent; }}
  ::-webkit-scrollbar-thumb {{ background: rgba(140,150,170,.22); border-radius: 9px; }}
  ::-webkit-scrollbar-thumb:hover {{ background: rgba(140,150,170,.36); }}

  /* ── Range input styling (reference match) ─────────────────────────── */
  input[type=range] {{
    -webkit-appearance: none;
    appearance: none;
    background: transparent;
  }}
  input[type=range]::-webkit-slider-runnable-track {{
    height: 4px;
    border-radius: 4px;
    background: var(--line2);
  }}
  input[type=range]::-webkit-slider-thumb {{
    -webkit-appearance: none;
    width: 15px;
    height: 15px;
    margin-top: -5.5px;
    border-radius: 50%;
    background: var(--cyan);
    cursor: pointer;
    box-shadow: 0 0 10px -1px var(--cyan);
  }}

  /* ── Skeleton shimmer — dark ───────────────────────────────────────── */
  .apex-skeleton {{
    background: linear-gradient(90deg, var(--panel) 25%, var(--elev) 50%, var(--panel) 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: {BORDER_RADIUS["md"]};
  }}

  /* ── Tooltip ───────────────────────────────────────────────────────── */
  [data-baseweb="tooltip"] {{
    background-color: var(--elev) !important;
    color: var(--text) !important;
    border-radius: {BORDER_RADIUS["sm"]} !important;
    border: 1px solid var(--line) !important;
    font-size: 0.75rem !important;
    padding: 0.35rem 0.65rem !important;
  }}

  /* ── Expander ──────────────────────────────────────────────────────── */
  .streamlit-expanderHeader {{
    color: var(--text) !important;
    background: var(--panel) !important;
    border: 1px solid var(--line) !important;
    border-radius: {BORDER_RADIUS["md"]} !important;
  }}

  /* ── Popover / dropdown menus ──────────────────────────────────────── */
  [data-baseweb="popover"] > div {{
    background-color: var(--elev) !important;
    border: 1px solid var(--line) !important;
  }}
  [data-baseweb="menu"] {{
    background-color: var(--elev) !important;
  }}
  [data-baseweb="menu"] li {{
    color: var(--text) !important;
  }}
  [data-baseweb="menu"] li:hover {{
    background-color: rgba(52, 225, 212, 0.08) !important;
  }}

  /* ── Date input ────────────────────────────────────────────────────── */
  [data-baseweb="calendar"] {{
    background-color: var(--elev) !important;
    color: var(--text) !important;
  }}

  /* ── Reduced motion ────────────────────────────────────────────────── */
  @media (prefers-reduced-motion: reduce) {{
    * {{
      animation: none !important;
      transition: none !important;
    }}
  }}
</style>
"""


def _brand_css_light() -> str:
    """Light mode CSS — mirrors dark CSS structure with light palette."""
    ff = TYPOGRAPHY["font_family"]
    C = COLORS_LIGHT
    bg = C["background"]
    surface = C["surface"]
    text_p = C["text_primary"]
    text_s = C["text_secondary"]
    primary = C["primary"]
    secondary = C["secondary"]
    border = C["border_solid"]
    glass_bg = C["glass_bg"]
    glass_border = C["glass_border"]

    t_fast = MOTION["duration_fast"]
    t_normal = MOTION["duration_normal"]
    ease_out = MOTION["ease_out"]
    ease_in_out = MOTION["ease_in_out"]

    return f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
  @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css');

  :root {{
    /* Legacy aliases — keep for existing components */
    --color-primary: {primary};
    --color-secondary: {secondary};
    --color-accent: {C["accent"]};
    --color-background: {bg};
    --color-surface: {surface};
    --color-text-primary: {text_p};
    --color-text-secondary: {text_s};
    --color-success: {C["success"]};
    --color-warning: {C["warning"]};
    --color-error: {C["error"]};
    --color-border: {border};
    --font-family: {ff};
    --gradient-blue: {GRADIENTS["blue_cyan"]};
    --glass-bg: {glass_bg};
    --glass-border: {glass_border};

    /* Signal Deck reference tokens — light mode (exact match to mockup) */
    --bg: #DDE2EA;
    --bg2: #EAEEF4;
    --panel: #FFFFFF;
    --panel2: #F4F6FA;
    --elev: #FFFFFF;
    --line: rgba(12,18,28,.13);
    --line2: rgba(12,18,28,.24);
    --text: #0A0E16;
    --text2: #414B5C;
    --text3: #5C6678;
    --cyan: #0B897E;
    --cyanInk: #FFFFFF;
    --green: #0F7A4D;
    --amber: #8A5E0A;
    --red: #C92F47;
    --dot: rgba(40,70,110,.22);
    --dotStar: rgba(50,80,120,.6);
    --headerBg: rgba(255,255,255,.7);
    --aura1: rgba(11,137,126,.12);
    --aura2: rgba(38,96,210,.09);
    --aura3: rgba(120,90,200,.07);
  }}

  /* ── Keyframe animations (Signal Deck reference) ───────────────────── */
  @keyframes ringkpi {{ from {{ opacity:1; }} }}
  @keyframes ringhero {{ from {{ opacity:1; }} }}
  @keyframes rise {{ from {{ opacity:1; }} }}
  @keyframes wirein {{ from {{ opacity:1; }} }}
  @keyframes pulseonce {{
    0%,100% {{ box-shadow:inset 0 0 0 0 rgba(255,92,114,0); }}
    35% {{ box-shadow:inset 2px 0 0 0 var(--red), 0 0 18px -4px rgba(255,92,114,.5); }}
  }}
  @keyframes blink {{
    0%,48% {{ opacity:1; }}
    50%,100% {{ opacity:0; }}
  }}
  @keyframes aura1 {{
    0% {{ transform:translate(0,0) scale(1); }}
    100% {{ transform:translate(7vw,6vh) scale(1.18); }}
  }}
  @keyframes aura2 {{
    0% {{ transform:translate(0,0) scale(1); }}
    100% {{ transform:translate(-6vw,7vh) scale(1.12); }}
  }}
  @keyframes aura3 {{
    0% {{ transform:translate(0,0) scale(1); }}
    100% {{ transform:translate(5vw,-6vh) scale(1.22); }}
  }}
  @keyframes floatA {{
    0% {{ transform:translate(0,0); }}
    100% {{ transform:translate(12px,-8px); }}
  }}
  @keyframes floatB {{
    0% {{ transform:translate(0,0); }}
    100% {{ transform:translate(-10px,6px); }}
  }}
  @keyframes floatC {{
    0% {{ transform:translate(0,0); }}
    100% {{ transform:translate(8px,10px); }}
  }}
  @keyframes floatD {{
    0% {{ transform:translate(0,0); }}
    100% {{ transform:translate(-6px,-12px); }}
  }}
  @keyframes floatE {{
    0% {{ transform:translate(0,0); }}
    100% {{ transform:translate(14px,4px); }}
  }}
  @keyframes floatF {{
    0% {{ transform:translate(0,0); }}
    100% {{ transform:translate(-8px,-6px); }}
  }}
  @keyframes twinkle {{
    0%,100% {{ opacity:.35; }}
    50% {{ opacity:.95; }}
  }}
  @keyframes shimmer {{
    0% {{ background-position: 200% 0; }}
    100% {{ background-position: -200% 0; }}
  }}

  html, body, [class*="css"] {{
    font-family: {ff} !important;
    color: var(--text) !important;
    background-color: var(--bg) !important;
  }}
  .stApp {{ background: var(--bg) !important; }}
  .block-container {{ max-width: 1600px; padding: 1.5rem 2rem; }}

  h1, h2, h3, h4, h5, h6 {{
    font-family: {ff} !important;
    color: var(--text) !important;
    font-weight: 700;
  }}
  p, span:not([data-testid="stIconMaterial"]), div, label {{ font-family: {ff} !important; }}

  /* Sidebar — light */
  section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, var(--panel), var(--bg2)) !important;
    border-right: 1px solid var(--line) !important;
    width: 260px !important; min-width: 260px !important;
    overflow-x: hidden !important;
    overflow-y: auto !important;
  }}
  section[data-testid="stSidebar"] > div {{ background: transparent !important; padding-top: 0.5rem !important; }}
  [data-testid="stSidebarHeader"] {{ padding: 0 !important; min-height: 0 !important; }}
  [data-testid="stSidebarContent"] {{ display: flex !important; flex-direction: column !important; }}
  [data-testid="stSidebarHeader"] {{ order: 0 !important; }}
  [data-testid="stSidebarUserContent"] {{ order: 1 !important; padding-top: 0 !important; }}
  [data-testid="stSidebarNav"] {{ order: 2 !important; }}
  [data-testid="stSidebarNavSeparator"] {{ display: none !important; }}
  section[data-testid="stSidebar"] .stMarkdown,
  section[data-testid="stSidebar"] label,
  section[data-testid="stSidebar"] span,
  section[data-testid="stSidebar"] p {{ color: var(--text2) !important; }}
  section[data-testid="stSidebar"] h1,
  section[data-testid="stSidebar"] h2,
  section[data-testid="stSidebar"] h3 {{ color: var(--text) !important; }}

  /* Sidebar nav */
  [data-testid="stSidebarNav"] {{
    padding: 0 0.5rem !important; margin-top: 0 !important;
    display: flex !important; flex-direction: column !important; flex: 1 !important;
  }}
  [data-testid="stSidebarNav"] ul {{ display: flex !important; flex-direction: column !important; flex: 1 !important; width: 100% !important; padding: 0 !important; margin: 0 !important; box-sizing: border-box !important; }}
  [data-testid="stSidebarNav"] ul li {{
    width: 100% !important; min-width: 0 !important;
    overflow: hidden !important; box-sizing: border-box !important;
  }}
  [data-testid="stSidebarNavLink"] {{
    display: flex !important; flex-direction: row !important; align-items: center !important;
    gap: 0.5rem !important; padding: 0.5rem 0.75rem !important; border-radius: {BORDER_RADIUS["md"]} !important;
    margin: 2px 0 !important; text-decoration: none !important;
    transition: background {t_fast} {ease_out} !important; overflow: hidden !important;
    width: 100% !important; min-width: 0 !important; max-width: 100% !important; box-sizing: border-box !important;
  }}
  section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] p,
  section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] [data-testid="stIconMaterial"] {{
    color: var(--text2) !important; font-weight: 500;
  }}
  [data-testid="stSidebarNavLink"]:hover {{ background: rgba(11, 137, 126, 0.06) !important; }}
  [data-testid="stSidebarNavLink"] > span {{
    display: inline-flex !important; align-items: center !important; flex-shrink: 0 !important;
  }}
  [data-testid="stSidebarNavLink"] > span::after {{ display: none !important; }}
  [data-testid="stSidebarNavLink"] > div {{
    flex: 1 1 0% !important; min-width: 0 !important; overflow: hidden !important; margin-left: 2px !important;
  }}
  [data-testid="stSidebarNavLink"] [data-testid="stMarkdownContainer"] {{
    min-width: 0 !important; overflow: hidden !important;
  }}
  [data-testid="stSidebarNavLink"] [data-testid="stMarkdownContainer"] p {{
    white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important;
    margin: 0 !important; font-size: 0.85rem !important;
  }}

  /* Pin Settings to bottom */
  [data-testid="stSidebarNav"] ul li:last-child {{
    margin-top: auto !important; border-top: 1px solid var(--line) !important; padding-top: 8px !important;
  }}
  /* Active nav — subtle teal highlight */
  [data-testid="stSidebarNavLink"][aria-current="page"] {{
    background: rgba(11, 137, 126, 0.08) !important; border-radius: {BORDER_RADIUS["md"]} !important;
    border-left: 3px solid var(--cyan) !important;
  }}
  section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] p {{
    color: var(--text) !important; font-weight: 600 !important;
  }}

  /* Collapsed sidebar — 64px icon rail */
  section[data-testid="stSidebar"][aria-expanded="false"] {{
    width: 64px !important; min-width: 64px !important; max-width: 64px !important;
    transform: none !important; margin-left: 0 !important;
    display: block !important; visibility: visible !important; overflow-x: hidden !important;
  }}
  section[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarUserContent"] {{ display: none !important; }}
  section[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarNav"] {{ padding: 0 !important; }}
  section[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarNavLink"] [data-testid="stMarkdownContainer"] {{ display: none !important; }}
  section[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarNavLink"] > div {{ display: none !important; }}
  section[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarNavLink"] {{
    width: 64px !important; justify-content: center !important;
    padding: 0.5rem 0 !important; margin: 2px 0 !important; box-sizing: border-box !important;
  }}
  section[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarNavLink"] > span {{
    display: inline-flex !important; align-items: center !important; justify-content: center !important;
  }}
  section[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarNavLink"][aria-current="page"] {{ background: rgba(11, 137, 126, 0.10) !important; }}
  [data-testid="stExpandSidebarButton"] button {{ background: transparent !important; border: none !important; box-shadow: none !important; }}
  [data-testid="stSidebarNavLink"] .e1lpckdq20 {{ margin-left: 0 !important; }}
  [data-testid="stSidebarNavLink"] [data-testid="stIconMaterial"] {{
    font-size: 18px !important; line-height: 1 !important; width: 18px !important;
    min-width: 18px !important; height: 18px !important; flex-shrink: 0 !important;
    display: inline-flex !important; align-items: center !important; justify-content: center !important;
    color: inherit !important; overflow: hidden !important; margin: 0 !important; padding: 0 !important;
  }}
  [data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"],
  [data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"] {{
    font-size: 0 !important; line-height: 0 !important; overflow: hidden !important;
    display: inline-flex !important; align-items: center !important; justify-content: center !important;
    width: 20px !important; height: 20px !important;
  }}
  [data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"]::before {{
    font-family: 'Font Awesome 6 Free' !important; font-weight: 900 !important; font-size: 14px !important;
    content: "\\f0c9" !important; color: var(--text2) !important;
  }}
  [data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"]::before {{
    font-family: 'Font Awesome 6 Free' !important; font-weight: 900 !important; font-size: 12px !important;
    content: "\\f053" !important; color: var(--text2) !important;
  }}

  /* Metrics */
  [data-testid="metric-container"] {{
    background: var(--panel); border: 1px solid var(--line);
    border-radius: 14px; padding: 1.25rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    transition: border-color {t_normal} {ease_in_out};
  }}
  [data-testid="metric-container"]:hover {{ border-color: var(--line2); }}
  [data-testid="metric-container"] label {{
    color: var(--text3) !important;
    font-family: 'JetBrains Mono', ui-monospace, monospace !important;
    font-size: 9px; font-weight: 500;
    text-transform: uppercase; letter-spacing: 0.15em;
  }}
  [data-testid="metric-container"] [data-testid="stMetricValue"] {{
    color: var(--text) !important; font-weight: 700;
    font-size: 30px; font-variant-numeric: tabular-nums; letter-spacing: -0.02em;
  }}

  /* Buttons */
  .stButton > button[kind="primary"] {{
    background: {GRADIENTS["blue_cyan"]} !important; color: var(--cyanInk) !important;
    border: none !important; font-weight: 600; border-radius: {BORDER_RADIUS["md"]};
    box-shadow: 0 2px 8px rgba(11, 137, 126, 0.2);
  }}
  :not(.filter-bar-container) > .stButton > button {{
    background: var(--panel) !important; color: var(--text) !important;
    border: 1px solid var(--line) !important; font-weight: 600; border-radius: {BORDER_RADIUS["md"]};
    transition: all {t_fast} {ease_out};
  }}
  :not(.filter-bar-container) > .stButton > button:hover {{
    border-color: var(--line2) !important;
  }}

  /* Form inputs */
  .stSelectbox > div > div,
  .stMultiSelect > div > div,
  .stTextInput > div > div > input,
  [data-baseweb="select"] {{
    background-color: var(--panel) !important; border-color: var(--line) !important;
    color: var(--text) !important; border-radius: {BORDER_RADIUS["md"]} !important;
  }}
  [data-baseweb="select"] > div {{
    background-color: var(--panel) !important; border-color: var(--line) !important; color: var(--text) !important;
  }}
  .stSelectbox label, .stMultiSelect label, .stTextInput label {{ color: var(--text2) !important; }}

  .stRadio label {{ color: var(--text2) !important; }}
  .stRadio [data-testid="stMarkdownContainer"] p {{ color: var(--text2) !important; }}
  [data-testid="stToggle"] label span {{ color: var(--text2) !important; }}

  /* Tables */
  .stDataFrame {{ border: 1px solid var(--line) !important; border-radius: {BORDER_RADIUS["md"]}; }}
  .stDataFrame [data-testid="StyledDataFrameDataCell"], .stDataFrame td {{
    color: var(--text) !important; background-color: transparent !important; border-color: var(--line) !important;
  }}
  .stDataFrame th {{
    color: var(--text2) !important; background-color: var(--panel2) !important; border-color: var(--line) !important;
  }}

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {{ border-bottom: 1px solid var(--line); background: transparent; }}
  .stTabs [data-baseweb="tab"] {{ color: var(--text2) !important; }}
  .stTabs [data-baseweb="tab"][aria-selected="true"] {{ color: var(--text) !important; border-bottom: 2px solid var(--cyan); }}

  hr {{ border-color: var(--line) !important; }}
  .stPlotlyChart {{ border-radius: {BORDER_RADIUS["md"]}; }}

  footer {{ visibility: hidden; }}
  [data-testid="stAppDeployButton"] {{ display: none !important; }}
  [data-testid="stMainMenu"] {{ display: none !important; }}
  header[data-testid="stHeader"] {{ background: var(--headerBg) !important; }}
  [data-testid="stDecoration"] {{ display: none !important; }}

  .stButton > button, [data-testid="stSidebarNavLink"], .stSelectbox, .stMultiSelect {{
    transition: all {t_fast} {ease_out};
  }}
  .apex-metric-value {{ font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }}

  /* ── Section headers (Signal Deck) ─────────────────────────────────── */
  .apex-section-header {{
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }}
  .apex-section-header .accent-bar {{
    width: 3px;
    height: 18px;
    border-radius: 2px;
    background: var(--cyan);
  }}
  .apex-section-header .accent-bar.critical {{
    background: var(--red);
  }}
  .apex-section-header .section-title {{
    font-size: 14px;
    font-weight: 600;
    color: var(--text);
  }}
  .apex-section-header .section-meta {{
    font-family: 'JetBrains Mono', ui-monospace, monospace;
    font-size: 10px;
    font-weight: 500;
    color: var(--text3);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-left: auto;
  }}

  /* ── Segmented controls (Signal Deck) ──────────────────────────────── */
  .apex-segmented-track {{
    background: var(--panel2);
    border-radius: 8px;
    padding: 2px;
    display: inline-flex;
    gap: 2px;
  }}
  .apex-segmented-track .segment {{
    padding: 4px 12px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 500;
    color: var(--text2);
    cursor: pointer;
    transition: all {t_fast} {ease_out};
  }}
  .apex-segmented-track .segment.active {{
    background: var(--cyan);
    color: var(--cyanInk);
  }}

  /* ── Scrollbars (reference match) ──────────────────────────────────── */
  ::-webkit-scrollbar {{ width: 9px; height: 9px; }}
  ::-webkit-scrollbar-track {{ background: transparent; }}
  ::-webkit-scrollbar-thumb {{ background: rgba(140,150,170,.22); border-radius: 9px; }}
  ::-webkit-scrollbar-thumb:hover {{ background: rgba(140,150,170,.36); }}

  /* ── Range input styling (reference match) ─────────────────────────── */
  input[type=range] {{
    -webkit-appearance: none;
    appearance: none;
    background: transparent;
  }}
  input[type=range]::-webkit-slider-runnable-track {{
    height: 4px;
    border-radius: 4px;
    background: var(--line2);
  }}
  input[type=range]::-webkit-slider-thumb {{
    -webkit-appearance: none;
    width: 15px;
    height: 15px;
    margin-top: -5.5px;
    border-radius: 50%;
    background: var(--cyan);
    cursor: pointer;
    box-shadow: 0 0 10px -1px var(--cyan);
  }}

  .apex-skeleton {{
    background: linear-gradient(90deg, var(--panel) 25%, var(--panel2) 50%, var(--panel) 75%);
    background-size: 200% 100%; animation: shimmer 1.5s infinite; border-radius: {BORDER_RADIUS["md"]};
  }}

  [data-baseweb="tooltip"] {{
    background-color: var(--panel) !important; color: var(--text) !important;
    border-radius: {BORDER_RADIUS["sm"]} !important; border: 1px solid var(--line) !important;
    font-size: 0.75rem !important; padding: 0.35rem 0.65rem !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
  }}

  .streamlit-expanderHeader {{
    color: var(--text) !important; background: var(--panel) !important;
    border: 1px solid var(--line) !important; border-radius: {BORDER_RADIUS["md"]} !important;
  }}

  [data-baseweb="popover"] > div {{ background-color: var(--panel) !important; border: 1px solid var(--line) !important; box-shadow: 0 4px 16px rgba(0,0,0,0.08) !important; }}
  [data-baseweb="menu"] {{ background-color: var(--panel) !important; }}
  [data-baseweb="menu"] li {{ color: var(--text) !important; }}
  [data-baseweb="menu"] li:hover {{ background-color: rgba(11, 137, 126, 0.06) !important; }}

  [data-baseweb="calendar"] {{ background-color: var(--panel) !important; color: var(--text) !important; }}

  /* AgGrid light */
  .ag-theme-streamlit {{
    --ag-background-color: var(--panel) !important;
    --ag-header-background-color: var(--panel2) !important;
    --ag-odd-row-background-color: var(--bg2) !important;
    --ag-row-hover-color: rgba(11, 137, 126, 0.04) !important;
    --ag-foreground-color: var(--text) !important;
    --ag-header-foreground-color: var(--text2) !important;
    --ag-border-color: var(--line) !important;
  }}

  /* ── Reduced motion ────────────────────────────────────────────────── */
  @media (prefers-reduced-motion: reduce) {{
    * {{
      animation: none !important;
      transition: none !important;
    }}
  }}
</style>
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def hex_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha:.3f})"


class _ColorAccessor:
    RED = _RED
    ONYX = _NAVY_RAISED
    PLATINUM = _GRAY_100
    SCARLET = _SCARLET
    MAHOGANY = _SCARLET
    IRON = _GRAY_300
    ALLOY = _GRAY_500
    NEAR_WHITE = _GRAY_100

    def __getitem__(self, key):
        return COLORS[key]

BRAND_COLORS = _ColorAccessor()


def get_active_colors() -> dict[str, str]:
    """Return the active color palette based on session state theme selection."""
    try:
        import streamlit as _st
        if _st.session_state.get("apex_theme") == "Light":
            return COLORS_LIGHT
    except Exception:
        pass
    return COLORS


def inject_brand_css():
    """Inject RVGT theme CSS — detects dark/light from session state."""
    import streamlit as _st
    theme = _st.session_state.get("apex_theme", "Dark")
    if theme == "Light":
        _st.markdown(_brand_css_light(), unsafe_allow_html=True)
    else:
        _st.markdown(_brand_css(), unsafe_allow_html=True)


def apply_brand(st, *, page_title: str = "RVGT | Marketing Intelligence",
                page_icon: str = "📊", layout: str = "wide",
                initial_sidebar_state: str = "expanded") -> None:
    st.set_page_config(
        page_title=page_title,
        page_icon=page_icon,
        layout=layout,
        initial_sidebar_state=initial_sidebar_state,
    )
    st.markdown(_brand_css(), unsafe_allow_html=True)
