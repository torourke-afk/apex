"""
RVGT Brand System — Dark Glassmorphism Edition
-----------------------------------------------
Inspired by Vision UI Dashboard. Deep navy backgrounds, glassmorphism cards,
gradient accents, neon glows. RVGT Red remains the primary accent.
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

# Core dark backgrounds
_NAVY = "#060B26"         # deepest background
_NAVY_CARD = "#0B1437"    # card / panel surface
_NAVY_RAISED = "#111C44"  # elevated card, sidebar
_NAVY_INPUT = "#0B1437"   # form input backgrounds

# RVGT accent — kept from original brand
_RED = "#FF0016"
_SCARLET = "#C00A0A"

# Gradient accent (Vision UI signature blue-to-cyan)
_BLUE = "#0075FF"
_CYAN = "#2CD9FF"

# Text
_WHITE = "#FFFFFF"
_GRAY_100 = "#E9EDF7"     # primary text on dark
_GRAY_300 = "#A0AEC0"     # secondary / muted text
_GRAY_500 = "#718096"     # tertiary / disabled

# Semantic
_GREEN = "#01B574"
_YELLOW = "#FFB547"
_RED_SOFT = "#E31A1A"

# Borders & glass
_BORDER = "rgba(226, 232, 240, 0.1)"
_GLASS_BG = "rgba(11, 20, 55, 0.75)"
_GLASS_BORDER = "rgba(226, 232, 240, 0.08)"

# ---------------------------------------------------------------------------
# Light mode palette
# ---------------------------------------------------------------------------

_LIGHT_BG = "#F7F8FC"
_LIGHT_SURFACE = "#FFFFFF"
_LIGHT_RAISED = "#F0F2F8"
_LIGHT_INPUT = "#FFFFFF"
_LIGHT_TEXT_PRIMARY = "#1A202C"
_LIGHT_TEXT_SECONDARY = "#718096"
_LIGHT_TEXT_MUTED = "#A0AEC0"
_LIGHT_BORDER = "rgba(0, 0, 0, 0.08)"
_LIGHT_GLASS_BG = "rgba(255, 255, 255, 0.85)"
_LIGHT_GLASS_BORDER = "rgba(0, 0, 0, 0.06)"
_LIGHT_BORDER_SOLID = "#E2E8F0"

COLORS_LIGHT: dict[str, str] = {
    "primary": _RED,
    "secondary": _BLUE,
    "accent": "#0066DD",
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
    # Brand primaries
    "primary": _RED,
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

# Chart palette
CHART_PALETTE: list[str] = [
    _BLUE,
    _CYAN,
    _RED,
    _GREEN,
    _YELLOW,
]

CHART_PALETTE_EXTENDED: list[str] = [
    _BLUE,
    _CYAN,
    _RED,
    _GREEN,
    _YELLOW,
    "#7B61FF",   # purple
    "#FF6B6B",   # coral
    _GRAY_300,
]

# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------

TYPOGRAPHY: dict = {
    "font_family": "'Plus Jakarta Sans', 'Inter', 'Helvetica Neue', Arial, sans-serif",
    "heading_font": "'Plus Jakarta Sans', 'Inter', 'Helvetica Neue', Arial, sans-serif",
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
    "blue_cyan": f"linear-gradient(135deg, {_BLUE} 0%, {_CYAN} 100%)",
    "card_bg": f"linear-gradient(127deg, rgba(6,11,38,0.94) 0%, rgba(26,35,82,0.50) 100%)",
    "sidebar": f"linear-gradient(180deg, {_NAVY_RAISED} 0%, {_NAVY} 100%)",
    "red_accent": f"linear-gradient(135deg, {_RED} 0%, {_SCARLET} 100%)",
    "success": f"linear-gradient(135deg, {_GREEN} 0%, #00D68F 100%)",
    "warning": f"linear-gradient(135deg, {_YELLOW} 0%, #FFD93D 100%)",
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
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
  @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css');

  /* ── CSS custom properties ─────────────────────────────────────────── */
  :root {{
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
  }}

  /* ── Global resets ─────────────────────────────────────────────────── */
  html, body, [class*="css"] {{
    font-family: {ff} !important;
    color: {text_p};
    background-color: {bg} !important;
  }}

  .stApp {{
    background: {bg} !important;
  }}

  /* ── Main content area ─────────────────────────────────────────────── */
  .block-container {{
    max-width: 1600px;
    padding: 1.5rem 2rem;
  }}

  /* ── Headings ──────────────────────────────────────────────────────── */
  h1, h2, h3, h4, h5, h6 {{
    font-family: {ff} !important;
    color: {text_p} !important;
    font-weight: 700;
  }}
  p, span:not([data-testid="stIconMaterial"]), div, label {{
    font-family: {ff} !important;
  }}

  /* ── Sidebar — dark gradient ───────────────────────────────────────── */
  section[data-testid="stSidebar"] {{
    background: {GRADIENTS["sidebar"]} !important;
    border-right: 1px solid {COLORS["glass_border"]} !important;
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
    color: {_GRAY_300} !important;
  }}
  section[data-testid="stSidebar"] h1,
  section[data-testid="stSidebar"] h2,
  section[data-testid="stSidebar"] h3 {{
    color: {_WHITE} !important;
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
    overflow: hidden !important;
    box-sizing: border-box !important;
  }}
  [data-testid="stSidebarNavLink"] {{
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    gap: 0.125rem !important;
    padding: 0.5rem 0.75rem !important;
    border-radius: {BORDER_RADIUS["md"]} !important;
    margin: 2px 0 !important;
    text-decoration: none !important;
    transition: background {t_fast} {ease_out} !important;
    overflow: hidden !important;
    width: 100% !important;
    min-width: 0 !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
  }}
  /* Text and icon color inside nav links */
  section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] p,
  section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] [data-testid="stIconMaterial"] {{
    color: {_GRAY_300} !important;
    font-weight: 500;
  }}
  [data-testid="stSidebarNavLink"]:hover {{
    background: rgba(0, 117, 255, 0.08) !important;
  }}

  /* ── Nav link inner layout ─────────────────────────────────────────── */
  /* > span = icon wrapper (Ws), > div = label container (sc/qs) */
  [data-testid="stSidebarNavLink"] > span {{
    display: inline-flex !important;
    align-items: center !important;
    flex-shrink: 0 !important;
  }}
  [data-testid="stSidebarNavLink"] > span::after {{ display: none !important; }}
  [data-testid="stSidebarNavLink"] > div {{
    flex: 1 1 0% !important;
    min-width: 0 !important;
    overflow: hidden !important;
    margin-left: 0 !important;
  }}
  [data-testid="stSidebarNavLink"] [data-testid="stMarkdownContainer"] {{
    min-width: 0 !important;
    overflow: hidden !important;
  }}
  [data-testid="stSidebarNavLink"] [data-testid="stMarkdownContainer"] p {{
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    margin: 0 !important;
    font-size: 0.85rem !important;
  }}

  /* ── Pin Settings to bottom of sidebar nav ────────────────────────────── */
  /* Push the last visible nav item (Settings) to the bottom */
  [data-testid="stSidebarNav"] ul li:last-child {{
    margin-top: auto !important;
    border-top: 1px solid {COLORS["glass_border"]} !important;
    padding-top: 8px !important;
  }}
  /* ── Active nav item — gradient badge ──────────────────────────────── */
  [data-testid="stSidebarNavLink"][aria-current="page"] {{
    background: {GRADIENTS["blue_cyan"]} !important;
    border-radius: {BORDER_RADIUS["md"]} !important;
  }}
  [data-testid="stSidebarNavLink"][aria-current="page"] span,
  [data-testid="stSidebarNavLink"][aria-current="page"] p {{
    color: {_WHITE} !important;
    font-weight: 700 !important;
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
    background: {GRADIENTS["blue_cyan"]} !important;
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
    color: {_GRAY_300} !important;
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
    color: {_GRAY_300} !important;
  }}

  /* ── Metric cards (st.metric) ──────────────────────────────────────── */
  [data-testid="metric-container"] {{
    background: {COLORS["glass_bg"]};
    border: 1px solid {COLORS["glass_border"]};
    border-radius: {BORDER_RADIUS["xl"]};
    padding: 1.25rem;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    transition: box-shadow {t_normal} {ease_in_out};
  }}
  [data-testid="metric-container"]:hover {{
    box-shadow: 0 4px 24px rgba(0, 117, 255, 0.12);
  }}
  [data-testid="metric-container"] label {{
    color: {_GRAY_300} !important;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }}
  [data-testid="metric-container"] [data-testid="stMetricValue"] {{
    color: {_WHITE} !important;
    font-weight: 700;
  }}

  /* ── Primary buttons — gradient (skip filter-bar buttons) ───────────── */
  .stButton > button[kind="primary"] {{
    background: {GRADIENTS["blue_cyan"]} !important;
    color: {_WHITE} !important;
    border: none !important;
    font-weight: 600;
    border-radius: {BORDER_RADIUS["md"]};
    transition: all {t_fast} {ease_out};
    box-shadow: 0 2px 12px rgba(0, 117, 255, 0.3);
  }}
  :not(.filter-bar-container) > .stButton > button {{
    background: {COLORS["glass_bg"]} !important;
    color: {_WHITE} !important;
    border: 1px solid {COLORS["glass_border"]} !important;
    font-weight: 600;
    border-radius: {BORDER_RADIUS["md"]};
    transition: all {t_fast} {ease_out};
  }}
  :not(.filter-bar-container) > .stButton > button:hover {{
    box-shadow: 0 4px 20px rgba(0, 117, 255, 0.2) !important;
    transform: translateY(-1px);
    border-color: rgba(0, 117, 255, 0.3) !important;
  }}

  /* ── Form inputs — dark themed ─────────────────────────────────────── */
  .stSelectbox > div > div,
  .stMultiSelect > div > div,
  .stTextInput > div > div > input,
  [data-baseweb="select"] {{
    background-color: {_NAVY_INPUT} !important;
    border-color: {COLORS["glass_border"]} !important;
    color: {_WHITE} !important;
    border-radius: {BORDER_RADIUS["md"]} !important;
  }}
  [data-baseweb="select"] > div {{
    background-color: {_NAVY_INPUT} !important;
    border-color: {COLORS["glass_border"]} !important;
    color: {_WHITE} !important;
  }}
  .stSelectbox label, .stMultiSelect label, .stTextInput label {{
    color: {_GRAY_300} !important;
  }}

  /* ── Radio buttons ─────────────────────────────────────────────────── */
  .stRadio label {{
    color: {_GRAY_300} !important;
  }}
  .stRadio [data-testid="stMarkdownContainer"] p {{
    color: {_GRAY_300} !important;
  }}

  /* ── Toggle ────────────────────────────────────────────────────────── */
  [data-testid="stToggle"] label span {{
    color: {_GRAY_300} !important;
  }}

  /* ── Dataframe / table ─────────────────────────────────────────────── */
  .stDataFrame {{
    border: 1px solid {COLORS["glass_border"]} !important;
    border-radius: {BORDER_RADIUS["md"]};
  }}
  .stDataFrame [data-testid="StyledDataFrameDataCell"],
  .stDataFrame td {{
    color: {_WHITE} !important;
    background-color: transparent !important;
    border-color: {COLORS["glass_border"]} !important;
  }}
  .stDataFrame th {{
    color: {_GRAY_300} !important;
    background-color: {_NAVY_RAISED} !important;
    border-color: {COLORS["glass_border"]} !important;
  }}

  /* ── AgGrid ────────────────────────────────────────────────────────── */
  .ag-theme-streamlit {{
    --ag-background-color: {_NAVY_CARD} !important;
    --ag-header-background-color: {_NAVY_RAISED} !important;
    --ag-odd-row-background-color: rgba(11, 20, 55, 0.5) !important;
    --ag-row-hover-color: rgba(0, 117, 255, 0.06) !important;
    --ag-foreground-color: {_WHITE} !important;
    --ag-header-foreground-color: {_GRAY_300} !important;
    --ag-border-color: {COLORS["glass_border"]} !important;
  }}

  /* ── Tabs ──────────────────────────────────────────────────────────── */
  .stTabs [data-baseweb="tab-list"] {{
    border-bottom: 1px solid {COLORS["glass_border"]};
    background: transparent;
  }}
  .stTabs [data-baseweb="tab"] {{
    color: {_GRAY_300} !important;
  }}
  .stTabs [data-baseweb="tab"][aria-selected="true"] {{
    color: {_WHITE} !important;
    border-bottom: 2px solid {_BLUE};
  }}

  /* ── Dividers ──────────────────────────────────────────────────────── */
  hr {{
    border-color: {COLORS["glass_border"]} !important;
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
    background: transparent !important;
  }}
  /* Style the sidebar expand button (visible when sidebar is collapsed) */
  [data-testid="stExpandSidebarButton"] {{
    color: {_GRAY_300} !important;
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

  /* ── Scrollbars — dark themed ──────────────────────────────────────── */
  ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
  ::-webkit-scrollbar-track {{ background: transparent; }}
  ::-webkit-scrollbar-thumb {{ background: {_GRAY_500}; border-radius: 3px; }}
  ::-webkit-scrollbar-thumb:hover {{ background: {_BLUE}; }}

  /* ── Skeleton shimmer — dark ───────────────────────────────────────── */
  .apex-skeleton {{
    background: linear-gradient(90deg, {_NAVY_CARD} 25%, {_NAVY_RAISED} 50%, {_NAVY_CARD} 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: {BORDER_RADIUS["md"]};
  }}
  @keyframes shimmer {{
    0% {{ background-position: 200% 0; }}
    100% {{ background-position: -200% 0; }}
  }}

  /* ── Tooltip ───────────────────────────────────────────────────────── */
  [data-baseweb="tooltip"] {{
    background-color: {_NAVY_RAISED} !important;
    color: {_WHITE} !important;
    border-radius: {BORDER_RADIUS["sm"]} !important;
    border: 1px solid {COLORS["glass_border"]} !important;
    font-size: 0.75rem !important;
    padding: 0.35rem 0.65rem !important;
  }}

  /* ── Expander ──────────────────────────────────────────────────────── */
  .streamlit-expanderHeader {{
    color: {_WHITE} !important;
    background: {COLORS["glass_bg"]} !important;
    border: 1px solid {COLORS["glass_border"]} !important;
    border-radius: {BORDER_RADIUS["md"]} !important;
  }}

  /* ── Popover / dropdown menus ──────────────────────────────────────── */
  [data-baseweb="popover"] > div {{
    background-color: {_NAVY_RAISED} !important;
    border: 1px solid {COLORS["glass_border"]} !important;
  }}
  [data-baseweb="menu"] {{
    background-color: {_NAVY_RAISED} !important;
  }}
  [data-baseweb="menu"] li {{
    color: {_GRAY_100} !important;
  }}
  [data-baseweb="menu"] li:hover {{
    background-color: rgba(0, 117, 255, 0.1) !important;
  }}

  /* ── Date input ────────────────────────────────────────────────────── */
  [data-baseweb="calendar"] {{
    background-color: {_NAVY_RAISED} !important;
    color: {_WHITE} !important;
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
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
  @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css');

  :root {{
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
  }}

  html, body, [class*="css"] {{
    font-family: {ff} !important;
    color: {text_p};
    background-color: {bg} !important;
  }}
  .stApp {{ background: {bg} !important; }}
  .block-container {{ max-width: 1600px; padding: 1.5rem 2rem; }}

  h1, h2, h3, h4, h5, h6 {{
    font-family: {ff} !important;
    color: {text_p} !important;
    font-weight: 700;
  }}
  p, span:not([data-testid="stIconMaterial"]), div, label {{ font-family: {ff} !important; }}

  /* Sidebar — light */
  section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {C["surface_raised"]} 0%, {C["surface"]} 100%) !important;
    border-right: 1px solid {glass_border} !important;
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
  section[data-testid="stSidebar"] p {{ color: {text_s} !important; }}
  section[data-testid="stSidebar"] h1,
  section[data-testid="stSidebar"] h2,
  section[data-testid="stSidebar"] h3 {{ color: {text_p} !important; }}

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
    color: {text_s} !important; font-weight: 500;
  }}
  [data-testid="stSidebarNavLink"]:hover {{ background: rgba(0, 117, 255, 0.06) !important; }}
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
    margin-top: auto !important; border-top: 1px solid {glass_border} !important; padding-top: 8px !important;
  }}
  /* Active nav */
  [data-testid="stSidebarNavLink"][aria-current="page"] {{
    background: {GRADIENTS["blue_cyan"]} !important; border-radius: {BORDER_RADIUS["md"]} !important;
  }}
  [data-testid="stSidebarNavLink"][aria-current="page"] span,
  [data-testid="stSidebarNavLink"][aria-current="page"] p {{ color: #FFFFFF !important; font-weight: 700 !important; }}

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
  section[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarNavLink"][aria-current="page"] {{ background: {GRADIENTS["blue_cyan"]} !important; }}
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
    content: "\\f0c9" !important; color: {text_s} !important;
  }}
  [data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"]::before {{
    font-family: 'Font Awesome 6 Free' !important; font-weight: 900 !important; font-size: 12px !important;
    content: "\\f053" !important; color: {text_s} !important;
  }}

  /* Metrics */
  [data-testid="metric-container"] {{
    background: {glass_bg}; border: 1px solid {glass_border};
    border-radius: {BORDER_RADIUS["xl"]}; padding: 1.25rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    transition: box-shadow {t_normal} {ease_in_out};
  }}
  [data-testid="metric-container"]:hover {{ box-shadow: 0 4px 16px rgba(0,0,0,0.08); }}
  [data-testid="metric-container"] label {{
    color: {text_s} !important; font-size: 0.72rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.06em;
  }}
  [data-testid="metric-container"] [data-testid="stMetricValue"] {{ color: {text_p} !important; font-weight: 700; }}

  /* Buttons */
  .stButton > button[kind="primary"] {{
    background: {GRADIENTS["blue_cyan"]} !important; color: #FFFFFF !important;
    border: none !important; font-weight: 600; border-radius: {BORDER_RADIUS["md"]};
    box-shadow: 0 2px 8px rgba(0, 117, 255, 0.2);
  }}
  :not(.filter-bar-container) > .stButton > button {{
    background: {surface} !important; color: {text_p} !important;
    border: 1px solid {border} !important; font-weight: 600; border-radius: {BORDER_RADIUS["md"]};
    transition: all {t_fast} {ease_out};
  }}
  :not(.filter-bar-container) > .stButton > button:hover {{
    box-shadow: 0 2px 12px rgba(0,0,0,0.08) !important;
    border-color: rgba(0, 117, 255, 0.3) !important;
  }}

  /* Form inputs */
  .stSelectbox > div > div,
  .stMultiSelect > div > div,
  .stTextInput > div > div > input,
  [data-baseweb="select"] {{
    background-color: {_LIGHT_INPUT} !important; border-color: {border} !important;
    color: {text_p} !important; border-radius: {BORDER_RADIUS["md"]} !important;
  }}
  [data-baseweb="select"] > div {{
    background-color: {_LIGHT_INPUT} !important; border-color: {border} !important; color: {text_p} !important;
  }}
  .stSelectbox label, .stMultiSelect label, .stTextInput label {{ color: {text_s} !important; }}

  .stRadio label {{ color: {text_s} !important; }}
  .stRadio [data-testid="stMarkdownContainer"] p {{ color: {text_s} !important; }}
  [data-testid="stToggle"] label span {{ color: {text_s} !important; }}

  /* Tables */
  .stDataFrame {{ border: 1px solid {glass_border} !important; border-radius: {BORDER_RADIUS["md"]}; }}
  .stDataFrame [data-testid="StyledDataFrameDataCell"], .stDataFrame td {{
    color: {text_p} !important; background-color: transparent !important; border-color: {glass_border} !important;
  }}
  .stDataFrame th {{
    color: {text_s} !important; background-color: {C["surface_raised"]} !important; border-color: {glass_border} !important;
  }}

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {{ border-bottom: 1px solid {glass_border}; background: transparent; }}
  .stTabs [data-baseweb="tab"] {{ color: {text_s} !important; }}
  .stTabs [data-baseweb="tab"][aria-selected="true"] {{ color: {text_p} !important; border-bottom: 2px solid {_BLUE}; }}

  hr {{ border-color: {glass_border} !important; }}
  .stPlotlyChart {{ border-radius: {BORDER_RADIUS["md"]}; }}

  footer {{ visibility: hidden; }}
  [data-testid="stAppDeployButton"] {{ display: none !important; }}
  [data-testid="stMainMenu"] {{ display: none !important; }}
  header[data-testid="stHeader"] {{ background: transparent !important; }}
  [data-testid="stDecoration"] {{ display: none !important; }}

  .stButton > button, [data-testid="stSidebarNavLink"], .stSelectbox, .stMultiSelect {{
    transition: all {t_fast} {ease_out};
  }}
  .apex-metric-value {{ font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }}

  ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
  ::-webkit-scrollbar-track {{ background: transparent; }}
  ::-webkit-scrollbar-thumb {{ background: #CBD5E0; border-radius: 3px; }}
  ::-webkit-scrollbar-thumb:hover {{ background: {_BLUE}; }}

  .apex-skeleton {{
    background: linear-gradient(90deg, {C["surface"]} 25%, {C["surface_raised"]} 50%, {C["surface"]} 75%);
    background-size: 200% 100%; animation: shimmer 1.5s infinite; border-radius: {BORDER_RADIUS["md"]};
  }}
  @keyframes shimmer {{ 0% {{ background-position: 200% 0; }} 100% {{ background-position: -200% 0; }} }}

  [data-baseweb="tooltip"] {{
    background-color: {surface} !important; color: {text_p} !important;
    border-radius: {BORDER_RADIUS["sm"]} !important; border: 1px solid {border} !important;
    font-size: 0.75rem !important; padding: 0.35rem 0.65rem !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
  }}

  .streamlit-expanderHeader {{
    color: {text_p} !important; background: {glass_bg} !important;
    border: 1px solid {glass_border} !important; border-radius: {BORDER_RADIUS["md"]} !important;
  }}

  [data-baseweb="popover"] > div {{ background-color: {surface} !important; border: 1px solid {border} !important; box-shadow: 0 4px 16px rgba(0,0,0,0.08) !important; }}
  [data-baseweb="menu"] {{ background-color: {surface} !important; }}
  [data-baseweb="menu"] li {{ color: {text_p} !important; }}
  [data-baseweb="menu"] li:hover {{ background-color: rgba(0, 117, 255, 0.06) !important; }}

  [data-baseweb="calendar"] {{ background-color: {surface} !important; color: {text_p} !important; }}

  /* AgGrid light */
  .ag-theme-streamlit {{
    --ag-background-color: {surface} !important;
    --ag-header-background-color: {C["surface_raised"]} !important;
    --ag-odd-row-background-color: {C["surface_sunken"]} !important;
    --ag-row-hover-color: rgba(0, 117, 255, 0.04) !important;
    --ag-foreground-color: {text_p} !important;
    --ag-header-foreground-color: {text_s} !important;
    --ag-border-color: {glass_border} !important;
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
