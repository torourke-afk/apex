"""
RVGT Geo Heatmap Component
--------------------------
Reusable geographic heatmap built on Plotly choropleth.
All colors sourced from src/config/brand.py — no hardcoded hex.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config.brand import COLORS, TYPOGRAPHY

# Default colorscale: Mahogany (low) → Red (mid) → near-white surface (high)
_DEFAULT_COLORSCALE: list[list] = [
    [0.0, COLORS["mahogany"]],   # #800000 — low values
    [0.5, COLORS["primary"]],    # #FF0016 — mid values
    [1.0, COLORS["surface"]],    # #FAFBFC — high values (near-white, not pure white)
]


def geo_heatmap(
    data: pd.DataFrame,
    value_col: str,
    label_col: str,
    colorscale: list | None = None,
    *,
    title: str | None = None,
    height: int = 450,
    locationmode: str = "USA-states",
    geojson: dict | None = None,
    featureidkey: str = "id",
    scope: str = "usa",
    hover_template: str | None = None,
    customdata: Any = None,
    reversescale: bool = False,
    zmin: float | None = None,
    zmax: float | None = None,
    colorbar_ticksuffix: str = "",
    on_select: str | None = None,
    selection_mode: str = "points",
    key: str | None = None,
) -> Any:
    """
    Render a branded geographic heatmap via Plotly choropleth.

    Parameters
    ----------
    data : pd.DataFrame
        DataFrame containing at least ``label_col`` and ``value_col`` columns.
    value_col : str
        Column name for the numeric values that drive the color intensity.
    label_col : str
        Column name for geographic identifiers (e.g. state abbreviations,
        FIPS codes, or custom DMA keys when ``geojson`` is provided).
    colorscale : list, optional
        Plotly colorscale override. Defaults to Mahogany → Red → surface.
        Pass ``None`` to use the RVGT brand default.
    title : str, optional
        Chart title. Preserved from figure if omitted.
    height : int
        Chart height in pixels (default 450).
    locationmode : str
        Plotly ``locationmode`` — ``"USA-states"``, ``"country names"``, or
        ``"geojson-id"`` (required when ``geojson`` is provided).
    geojson : dict, optional
        GeoJSON FeatureCollection for custom regions (DMAs, counties, etc.).
        When provided, ``locationmode`` should be ``"geojson-id"``.
    featureidkey : str
        GeoJSON feature property path used to match ``label_col`` values
        (e.g. ``"properties.name"`` or ``"id"``). Only used with ``geojson``.
    scope : str
        Map scope passed to ``fig.update_geos()`` — ``"usa"``, ``"world"``,
        ``"north america"``, etc.
    hover_template : str, optional
        Custom Plotly hover template string. A sensible default is built from
        ``label_col`` and ``value_col`` when omitted.
    customdata : array-like, optional
        Extra data array attached to each point for use in ``hover_template``
        via ``%{customdata[n]}`` references. Passed directly to the choropleth
        trace's ``customdata`` argument.
    reversescale : bool
        Reverse the colorscale direction (default False). Useful when high
        values should map to lighter colors (e.g. retention rate).
    zmin : float, optional
        Lower bound of the color axis. Inferred from data when omitted.
    zmax : float, optional
        Upper bound of the color axis. Inferred from data when omitted.
    colorbar_ticksuffix : str
        Suffix appended to colorbar tick labels (e.g. ``"%"``).
    on_select : str, optional
        Streamlit selection trigger — ``"rerun"`` to rerun the app when the
        user clicks a point, or ``None`` to disable selection (default).
    selection_mode : str
        Plotly selection mode when ``on_select`` is set — ``"points"``,
        ``"box"``, or ``"lasso"`` (default ``"points"``).
    key : str, optional
        Streamlit widget key for the chart. Required when multiple geo heatmaps
        appear on the same page, or when ``on_select`` is used.

    Returns
    -------
    dict or None
        When ``on_select`` is set, returns the Streamlit selection state dict
        (``{"selection": {"points": [...]}}``) so callers can drill into
        clicked regions. Returns ``None`` when ``on_select`` is ``None``.
    """
    if colorscale is None:
        colorscale = _DEFAULT_COLORSCALE

    if hover_template is None:
        hover_template = (
            f"<b>%{{location}}</b><br>{value_col}: %{{z:,.2f}}<extra></extra>"
        )

    # Build choropleth trace
    choropleth_kwargs: dict = dict(
        locations=data[label_col],
        z=data[value_col],
        colorscale=colorscale,
        reversescale=reversescale,
        locationmode=locationmode,
        hovertemplate=hover_template,
        marker_line_color=COLORS["border"],
        marker_line_width=0.5,
        colorbar=dict(
            title=dict(
                text=value_col,
                font=dict(
                    family=TYPOGRAPHY["font_family"],
                    color=COLORS["text_primary"],
                    size=12,
                ),
            ),
            tickfont=dict(
                family=TYPOGRAPHY["font_family"],
                color=COLORS["text_secondary"],
                size=11,
            ),
            bgcolor=COLORS["surface"],
            bordercolor=COLORS["border"],
            borderwidth=1,
            ticksuffix=colorbar_ticksuffix,
        ),
    )

    if customdata is not None:
        choropleth_kwargs["customdata"] = (
            customdata if isinstance(customdata, np.ndarray) else np.array(customdata)
        )

    if zmin is not None:
        choropleth_kwargs["zmin"] = zmin
    if zmax is not None:
        choropleth_kwargs["zmax"] = zmax

    if geojson is not None:
        choropleth_kwargs["geojson"] = geojson
        choropleth_kwargs["featureidkey"] = featureidkey

    fig = go.Figure(go.Choropleth(**choropleth_kwargs))

    # Geo layout — projection and background use brand colors
    fig.update_geos(
        scope=scope,
        showframe=False,
        showcoastlines=True,
        coastlinecolor=COLORS["border"],
        showland=True,
        landcolor=COLORS["background"],
        showlakes=True,
        lakecolor=COLORS["surface"],
        showocean=True,
        oceancolor=COLORS["background"],
        showcountries=True,
        countrycolor=COLORS["border"],
        showsubunits=True,
        subunitcolor=COLORS["alloy"],
        bgcolor=COLORS["surface"],
    )

    # Apply brand layout (mirrors branded_chart without calling it, so we can
    # pass on_select and key directly to st.plotly_chart and capture the return)
    layout_update: dict = dict(
        height=height,
        paper_bgcolor=COLORS["surface"],
        plot_bgcolor=COLORS["surface"],
        font=dict(
            family=TYPOGRAPHY["font_family"],
            color=COLORS["text_primary"],
            size=13,
        ),
        margin=dict(l=0, r=0, t=48 if title else 0, b=0),
        dragmode=False,
    )
    if title is not None:
        layout_update["title"] = dict(
            text=title,
            font=dict(
                family=TYPOGRAPHY["font_family"],
                color=COLORS["text_primary"],
                size=16,
            ),
            x=0,
            xanchor="left",
        )
    fig.update_layout(**layout_update)

    # Render — with or without selection support
    plotly_kwargs: dict = {"use_container_width": True}
    if key is not None:
        plotly_kwargs["key"] = key
    if on_select is not None:
        plotly_kwargs["on_select"] = on_select
        plotly_kwargs["selection_mode"] = selection_mode
        return st.plotly_chart(fig, **plotly_kwargs)

    st.plotly_chart(fig, **plotly_kwargs)
    return None
