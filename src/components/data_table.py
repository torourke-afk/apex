"""
RVGT Branded Data Table
-----------------------
Wraps streamlit-aggrid with RVGT brand styling.
All colors sourced from src/config/brand.py — no hardcoded hex values.
"""

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

from src.config.brand import COLORS, TYPOGRAPHY


# --------------------------------------------------------------------------- #
# Cell renderer helpers                                                         #
# --------------------------------------------------------------------------- #

def badge_cell_renderer(thresholds: dict = None) -> JsCode:
    """Return a JsCode cell renderer that shows a colored badge.

    Parameters
    ----------
    thresholds : dict
        {"green": 3.0, "amber": 1.5}
        Values >= green get a green badge, >= amber get amber, below get red.
        Defaults to ROAS thresholds if omitted.
    """
    if thresholds is None:
        thresholds = {"green": 3.0, "amber": 1.5}

    green_threshold = thresholds.get("green", 3.0)
    amber_threshold = thresholds.get("amber", 1.5)

    success_color = COLORS["success"]    # #2E7D52
    warning_color = COLORS["warning"]    # #C97B1A
    error_color = COLORS["error"]        # #C00A0A

    return JsCode(f"""
        class BadgeCellRenderer {{
            init(params) {{
                const val = parseFloat(params.value);
                let bg, color;
                if (val >= {green_threshold}) {{
                    bg = 'rgba(46,125,82,0.12)';
                    color = '{success_color}';
                }} else if (val >= {amber_threshold}) {{
                    bg = 'rgba(201,123,26,0.12)';
                    color = '{warning_color}';
                }} else {{
                    bg = 'rgba(192,10,10,0.12)';
                    color = '{error_color}';
                }}
                const display = isNaN(val) ? params.value : val.toFixed(2) + 'x';
                this.eGui = document.createElement('span');
                this.eGui.style.cssText = [
                    'display:inline-flex',
                    'align-items:center',
                    'padding:2px 8px',
                    'border-radius:9999px',
                    'font-size:0.75rem',
                    'font-weight:600',
                    'line-height:1.4',
                    `background:${{bg}}`,
                    `color:${{color}}`,
                ].join(';');
                this.eGui.textContent = display;
            }}
            getGui() {{ return this.eGui; }}
        }}
    """)


def progress_bar_renderer(max_value: float = 100) -> JsCode:
    """Return a JsCode cell renderer that shows an inline progress bar.

    Fill color: green <80%, amber 80–95%, red >95%.
    """
    success_color = COLORS["success"]
    warning_color = COLORS["warning"]
    error_color = COLORS["error"]
    border_color = COLORS["border"]
    text_secondary = COLORS["text_secondary"]

    return JsCode(f"""
        class ProgressBarRenderer {{
            init(params) {{
                const raw = parseFloat(params.value) || 0;
                const pct = Math.min(raw / {max_value} * 100, 100);
                let barColor;
                if (pct < 80) {{
                    barColor = '{success_color}';
                }} else if (pct <= 95) {{
                    barColor = '{warning_color}';
                }} else {{
                    barColor = '{error_color}';
                }}
                this.eGui = document.createElement('div');
                this.eGui.style.cssText = 'display:flex;align-items:center;gap:6px;width:100%;';

                const track = document.createElement('div');
                track.style.cssText = [
                    'flex:1',
                    'height:6px',
                    'border-radius:3px',
                    `background:{border_color}`,
                    'overflow:hidden',
                ].join(';');

                const fill = document.createElement('div');
                fill.style.cssText = [
                    `width:${{pct}}%`,
                    'height:100%',
                    'border-radius:3px',
                    `background:${{barColor}}`,
                    'transition:width 300ms ease',
                ].join(';');

                const label = document.createElement('span');
                label.style.cssText = 'font-size:0.75rem;color:{text_secondary};min-width:32px;text-align:right;';
                label.textContent = pct.toFixed(0) + '%';

                track.appendChild(fill);
                this.eGui.appendChild(track);
                this.eGui.appendChild(label);
            }}
            getGui() {{ return this.eGui; }}
        }}
    """)


def status_dot_renderer() -> JsCode:
    """Return a JsCode cell renderer for status column (Active/Paused/Stopped)."""
    success_color = COLORS["success"]
    warning_color = COLORS["warning"]
    error_color = COLORS["error"]
    text_primary = COLORS["text_primary"]

    return JsCode(f"""
        class StatusDotRenderer {{
            init(params) {{
                const status = (params.value || '').toLowerCase();
                let dotColor;
                if (status === 'active') {{
                    dotColor = '{success_color}';
                }} else if (status === 'paused') {{
                    dotColor = '{warning_color}';
                }} else {{
                    dotColor = '{error_color}';
                }}
                this.eGui = document.createElement('div');
                this.eGui.style.cssText = 'display:flex;align-items:center;gap:6px;';

                const dot = document.createElement('span');
                dot.style.cssText = [
                    'display:inline-block',
                    'width:8px',
                    'height:8px',
                    'border-radius:50%',
                    `background:${{dotColor}}`,
                    'flex-shrink:0',
                ].join(';');

                const text = document.createElement('span');
                text.style.cssText = `font-size:0.8125rem;color:{text_primary};`;
                text.textContent = params.value || '';

                this.eGui.appendChild(dot);
                this.eGui.appendChild(text);
            }}
            getGui() {{ return this.eGui; }}
        }}
    """)


def configure_campaign_table(gb: GridOptionsBuilder) -> None:
    """Pre-configure columns for the standard campaign performance table."""
    gb.configure_column("Campaign", pinned="left", width=200)
    gb.configure_column("Status", cellRenderer=status_dot_renderer(), width=100)
    gb.configure_column(
        "ROAS",
        cellRenderer=badge_cell_renderer({"green": 3.0, "amber": 1.0}),
        width=100,
    )
    gb.configure_column(
        "Budget Pace",
        cellRenderer=progress_bar_renderer(),
        width=140,
    )


# --------------------------------------------------------------------------- #
# Main table component                                                          #
# --------------------------------------------------------------------------- #

def data_table(
    df: pd.DataFrame,
    sortable: bool = True,
    filterable: bool = True,
    paginated: bool = True,
    page_size: int = 20,
    height: int = 400,
    key: str = None,
) -> None:
    """
    Render a branded AG Grid data table with RVGT styling.

    Parameters
    ----------
    df : pd.DataFrame
        Data to display.
    sortable : bool
        Enable column sorting (default True).
    filterable : bool
        Enable column filters (default True).
    paginated : bool
        Enable pagination (default True).
    page_size : int
        Rows per page when paginated (default 20).
    height : int
        Grid height in pixels (default 400).
    key : str, optional
        Streamlit widget key for deduplication in multi-table layouts.
    """
    # ------------------------------------------------------------------ #
    # Colors — all from brand tokens, no hardcoded hex                     #
    # ------------------------------------------------------------------ #
    header_bg = COLORS["background"]      # Platinum #F1F4F7 (lightened from Onyx)
    header_text = COLORS["text_primary"]  # Onyx #303A42
    row_odd = COLORS["surface"]           # near-white  #FAFBFC
    row_even = COLORS["background"]       # platinum  #F1F4F7
    border_color = COLORS["border"]       # ALLOY dividers
    text_color = COLORS["text_primary"]   # ONYX body text
    font_family = TYPOGRAPHY["font_family"]

    # RVGT Red at 4% opacity for row hover
    hover_bg = "rgba(255, 0, 22, 0.04)"

    # ------------------------------------------------------------------ #
    # AG Grid options                                                       #
    # ------------------------------------------------------------------ #
    gb = GridOptionsBuilder.from_dataframe(df)

    gb.configure_default_column(
        sortable=sortable,
        filter=filterable,
        resizable=True,
        editable=False,
    )

    if paginated:
        gb.configure_pagination(
            paginationAutoPageSize=False,
            paginationPageSize=page_size,
        )

    gb.configure_grid_options(
        domLayout="normal",
        rowHeight=40,
        headerHeight=44,
        suppressMovableColumns=False,
        animateRows=True,
        suppressColumnVirtualisation=False,
    )

    # Alternating row background via getRowStyle JS callback
    alternating_row_style = JsCode(f"""
        function(params) {{
            if (params.node.rowIndex % 2 === 0) {{
                return {{ 'background-color': '{row_odd}' }};
            }} else {{
                return {{ 'background-color': '{row_even}' }};
            }}
        }}
    """)
    gb.configure_grid_options(getRowStyle=alternating_row_style)

    grid_options = gb.build()

    # ------------------------------------------------------------------ #
    # Custom CSS — brand header, hover, borders, font                      #
    # ------------------------------------------------------------------ #
    custom_css = {
        # Header row — light Platinum background
        ".ag-header": {
            "background-color": f"{header_bg} !important",
            "border-bottom": f"2px solid {border_color} !important",
        },
        ".ag-header-cell-label": {
            "color": f"{header_text} !important",
            "font-family": font_family,
            "font-weight": "600",
            "font-size": "0.8125rem",
            "text-transform": "uppercase",
            "letter-spacing": "0.04em",
        },
        ".ag-header-cell": {
            "background-color": f"{header_bg} !important",
        },
        ".ag-header-cell:hover": {
            "background-color": f"{COLORS['surface_sunken']} !important",
        },
        # Sort/filter icons in header
        ".ag-icon": {
            "color": f"{header_text} !important",
        },
        # Row hover — subtle RVGT Red tint
        ".ag-row-hover": {
            "background-color": f"{hover_bg} !important",
        },
        # Cell text — no right border
        ".ag-cell": {
            "color": f"{text_color}",
            "font-family": font_family,
            "font-size": "0.875rem",
            "border-right": "none",
            "display": "flex",
            "align-items": "center",
        },
        # Row borders
        ".ag-row": {
            "border-bottom": f"1px solid {border_color} !important",
        },
        # Root grid border
        ".ag-root-wrapper": {
            "border": f"1px solid {border_color}",
            "border-radius": "4px",
        },
        # Pagination bar
        ".ag-paging-panel": {
            "background-color": f"{row_even}",
            "color": f"{text_color}",
            "font-family": font_family,
            "font-size": "0.8125rem",
            "border-top": f"1px solid {border_color}",
        },
        # Filter panel
        ".ag-filter-toolpanel-header": {
            "background-color": f"{row_even}",
        },
    }

    # ------------------------------------------------------------------ #
    # Render                                                                #
    # ------------------------------------------------------------------ #
    AgGrid(
        df,
        gridOptions=grid_options,
        custom_css=custom_css,
        height=height,
        update_mode=GridUpdateMode.NO_UPDATE,
        allow_unsafe_jscode=True,
        fit_columns_on_grid_load=True,
        key=key,
    )


def render_campaign_table(
    df: pd.DataFrame,
    key: str = None,
    height: int = 280,
) -> None:
    """Render the campaign performance table with RVGT brand styling.

    Expects a DataFrame with columns: Campaign, Status, Spend, Revenue,
    ROAS, Funded, Budget Pace.  Spend/Revenue should be pre-formatted
    strings; ROAS and Budget Pace should be raw numeric values.
    """
    header_bg = COLORS["background"]
    header_text = COLORS["text_primary"]
    row_odd = COLORS["surface"]
    row_even = COLORS["background"]
    border_color = COLORS["border"]
    text_color = COLORS["text_primary"]
    font_family = TYPOGRAPHY["font_family"]
    hover_bg = "rgba(255, 0, 22, 0.04)"

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(sortable=True, filter=False, resizable=True, editable=False)

    gb.configure_column("Campaign", pinned="left", width=220, cellStyle={"fontWeight": "600"})
    gb.configure_column("Status", cellRenderer=status_dot_renderer(), width=110)
    gb.configure_column("Spend", width=100)
    gb.configure_column("Revenue", width=110)
    gb.configure_column(
        "ROAS",
        cellRenderer=badge_cell_renderer({"green": 3.0, "amber": 1.0}),
        width=100,
    )
    gb.configure_column("Funded", width=100)
    gb.configure_column(
        "Budget Pace",
        cellRenderer=progress_bar_renderer(max_value=100),
        width=160,
    )

    gb.configure_grid_options(
        domLayout="normal",
        rowHeight=44,
        headerHeight=44,
        suppressMovableColumns=True,
        animateRows=True,
    )

    alternating_row_style = JsCode(f"""
        function(params) {{
            if (params.node.rowIndex % 2 === 0) {{
                return {{ 'background-color': '{row_odd}' }};
            }} else {{
                return {{ 'background-color': '{row_even}' }};
            }}
        }}
    """)
    gb.configure_grid_options(getRowStyle=alternating_row_style)

    grid_options = gb.build()

    custom_css = {
        ".ag-header": {
            "background-color": f"{header_bg} !important",
            "border-bottom": f"2px solid {border_color} !important",
        },
        ".ag-header-cell-label": {
            "color": f"{header_text} !important",
            "font-family": font_family,
            "font-weight": "600",
            "font-size": "0.8125rem",
            "text-transform": "uppercase",
            "letter-spacing": "0.04em",
        },
        ".ag-header-cell": {
            "background-color": f"{header_bg} !important",
        },
        ".ag-header-cell:hover": {
            "background-color": f"{COLORS['surface_sunken']} !important",
        },
        ".ag-icon": {
            "color": f"{header_text} !important",
        },
        ".ag-row-hover": {
            "background-color": f"{hover_bg} !important",
        },
        ".ag-cell": {
            "color": f"{text_color}",
            "font-family": font_family,
            "font-size": "0.875rem",
            "border-right": "none",
            "display": "flex",
            "align-items": "center",
        },
        ".ag-row": {
            "border-bottom": f"1px solid {border_color} !important",
        },
        ".ag-root-wrapper": {
            "border": f"1px solid {border_color}",
            "border-radius": "4px",
        },
    }

    AgGrid(
        df,
        gridOptions=grid_options,
        custom_css=custom_css,
        height=height,
        update_mode=GridUpdateMode.NO_UPDATE,
        allow_unsafe_jscode=True,
        fit_columns_on_grid_load=True,
        key=key,
    )
