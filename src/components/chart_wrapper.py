"""
RVGT Branded Chart Wrapper
--------------------------
Applies RVGT brand styling to Plotly figures and renders them via Streamlit.
All colors and fonts are sourced from src/config/brand.py — no hardcoded values.
"""

import streamlit as st
import plotly.graph_objects as go

from src.config.brand import BORDER_RADIUS, CHART_PALETTE, COLORS, TYPOGRAPHY


def brand_color_sequence() -> list:
    """Returns ordered list of brand colors for Plotly trace color_discrete_sequence."""
    return list(CHART_PALETTE)


def branded_chart(fig, title: str = None, height: int = 400, key: str = None) -> None:
    """
    Applies RVGT brand styling to a Plotly figure and renders it via st.plotly_chart.

    Handles bar, line, scatter, and pie chart types. Modifies the figure in-place
    before rendering — does not return the figure.

    Parameters
    ----------
    fig : plotly.graph_objects.Figure
        A Plotly figure to brand and render.
    title : str, optional
        Chart title. If None, the existing figure title is preserved.
    height : int
        Chart height in pixels (default 400).
    key : str, optional
        Streamlit chart key for identity stability across reruns.
    """
    font_family = TYPOGRAPHY["font_family"]
    text_primary = COLORS["text_primary"]
    text_secondary = COLORS["text_secondary"]
    surface = COLORS["surface"]
    border = COLORS["border"]

    # Apply color sequence to all traces that support it
    color_seq = brand_color_sequence()
    for i, trace in enumerate(fig.data):
        color = color_seq[i % len(color_seq)]
        trace_type = trace.type if hasattr(trace, "type") else ""

        if trace_type == "pie":
            # Pie traces use marker.colors for slice colors
            if not (hasattr(trace, "marker") and trace.marker and trace.marker.colors):
                trace.update(marker={"colors": color_seq})
        elif trace_type in ("bar", "scatter", "scattergl"):
            # Only override if no explicit color is set on the trace
            if not (hasattr(trace, "marker") and trace.marker and trace.marker.color):
                trace.update(marker={"color": color})
        else:
            # Generic fallback: attempt marker color
            try:
                if not (hasattr(trace, "marker") and trace.marker and trace.marker.color):
                    trace.update(marker={"color": color})
            except Exception:
                pass

    # Build layout update dict
    layout_update = dict(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family=font_family,
            color=text_primary,
            size=13,
        ),
        xaxis=dict(
            gridcolor=border,
            linecolor=border,
            tickfont=dict(color=text_secondary),
            title_font=dict(color=text_primary),
        ),
        yaxis=dict(
            gridcolor=border,
            linecolor=border,
            tickfont=dict(color=text_secondary),
            title_font=dict(color=text_primary),
        ),
        legend=dict(
            font=dict(color=text_primary),
            bgcolor=surface,
            bordercolor=border,
            borderwidth=1,
        ),
        margin=dict(l=40, r=20, t=48 if title else 20, b=40),
    )

    if title is not None:
        layout_update["title"] = dict(
            text=title,
            font=dict(
                family=font_family,
                color=text_primary,
                size=16,
            ),
            x=0,
            xanchor="left",
        )

    fig.update_layout(**layout_update)

    st.plotly_chart(fig, use_container_width=True, key=key)


# Alias matching the spec API name
branded_plotly = branded_chart


def waterfall_chart(
    stages: list,
    values: list,
    rates: list,
    title: str = None,
    height: int = 400,
    bar_colors: list | None = None,
    benchmarks: list | None = None,
    text_labels: list | None = None,
    key: str | None = None,
) -> None:
    """
    Renders a branded funnel/waterfall bar chart for conversion funnel stages.

    Parameters
    ----------
    stages : list[str]
        Stage labels, e.g. ["Impressions", "Clicks", "Leads", "Conversions"].
    values : list[float]
        Absolute value at each stage.
    rates : list[float]
        Conversion rates between stages (len == len(stages) - 1).
    title : str, optional
        Chart title.
    height : int
        Chart height in pixels (default 400).
    bar_colors : list[str], optional
        Per-bar colors (e.g. benchmark signal colors). Defaults to CHART_PALETTE cycling.
    benchmarks : list[float], optional
        Absolute benchmark values per stage. If provided, adds a dotted overlay line.
    text_labels : list[str], optional
        Pre-built HTML text labels for each bar. If omitted, labels are generated from
        values and rates.
    key : str, optional
        Streamlit chart key for identity stability across reruns.
    """
    font_family = TYPOGRAPHY["font_family"]
    text_primary = COLORS["text_primary"]
    text_secondary = COLORS["text_secondary"]
    surface = COLORS["surface"]
    border = COLORS["border"]
    near_white = COLORS["background"]

    resolved_bar_colors = bar_colors if bar_colors is not None else (
        [list(CHART_PALETTE)[i % len(CHART_PALETTE)] for i in range(len(stages))]
    )

    # Build text labels if not provided
    if text_labels is None:
        text_labels = []
        for i, v in enumerate(values):
            label = f"{v:,.0f}"
            if i < len(rates):
                label += f"<br><span style='font-size:10px'>{rates[i]:.1%} →</span>"
            text_labels.append(label)

    fig = go.Figure(
        go.Bar(
            x=stages,
            y=values,
            marker_color=resolved_bar_colors,
            text=text_labels,
            textposition="outside",
            textfont=dict(family=font_family, color=text_primary, size=12),
            hovertemplate="<b>%{x}</b><br>Value: %{y:,.0f}<extra></extra>",
        )
    )

    show_legend = benchmarks is not None
    if benchmarks is not None:
        fig.add_trace(
            go.Scatter(
                x=stages,
                y=benchmarks,
                name="Benchmark",
                mode="lines+markers",
                line=dict(color=COLORS["success"], width=1.5, dash="dot"),
                marker=dict(size=6, color=COLORS["success"], symbol="diamond"),
                hovertemplate="<b>%{x} — Benchmark</b><br>%{y:,.0f}<extra></extra>",
            )
        )

    layout_update = dict(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=font_family, color=text_primary, size=13),
        xaxis=dict(
            gridcolor=border,
            linecolor=border,
            tickfont=dict(color=text_secondary),
        ),
        yaxis=dict(
            gridcolor=COLORS["alloy"],
            linecolor=border,
            tickfont=dict(color=text_secondary),
            tickformat=",",
        ),
        showlegend=show_legend,
        margin=dict(l=40, r=20, t=48 if (title or show_legend) else 20, b=40),
    )

    if show_legend:
        layout_update["legend"] = dict(
            font=dict(family=font_family, color=text_primary, size=12),
            bgcolor=surface,
            bordercolor=border,
            borderwidth=1,
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        )

    if title is not None:
        layout_update["title"] = dict(
            text=title,
            font=dict(family=font_family, color=text_primary, size=16),
            x=0,
            xanchor="left",
        )

    fig.update_layout(**layout_update)
    st.plotly_chart(fig, use_container_width=True, key=key)


def branded_chart_card(
    fig: go.Figure,
    title: str,
    subtitle: str = None,
    height: int = 300,
    toggles: list[str] = None,
    key: str = None,
) -> None:
    """
    Renders a Plotly figure inside a styled card container with header.

    Applies RVGT brand styling with transparent backgrounds so the card
    surface shows through.

    Parameters
    ----------
    fig : plotly.graph_objects.Figure
        A Plotly figure to brand and render.
    title : str
        Card heading.
    subtitle : str, optional
        Secondary description rendered below the title.
    height : int
        Chart height in pixels (default 300).
    toggles : list[str], optional
        Pill-style labels rendered at top-right of the card header,
        e.g. ["Monthly", "Weekly"]. First item is rendered as active.
    key : str, optional
        Streamlit chart key for identity stability across reruns.
    """
    heading_font = TYPOGRAPHY["heading_font"]
    text_primary = COLORS["text_primary"]
    text_secondary = COLORS["text_secondary"]
    primary = COLORS["primary"]
    surface = COLORS["surface"]
    border = COLORS["border"]
    radius = BORDER_RADIUS["lg"]

    # Build toggle buttons HTML
    toggles_html = ""
    if toggles:
        buttons = []
        for i, label in enumerate(toggles):
            if i == 0:
                btn_style = (
                    f"display:inline-flex;align-items:center;padding:3px 10px;"
                    f"border-radius:9999px;border:1px solid {primary};"
                    f"background:rgba(255,0,22,0.08);font-family:{heading_font};"
                    f"font-size:0.75rem;font-weight:500;color:{primary};"
                )
            else:
                btn_style = (
                    f"display:inline-flex;align-items:center;padding:3px 10px;"
                    f"border-radius:9999px;border:1px solid {border};"
                    f"background:transparent;font-family:{heading_font};"
                    f"font-size:0.75rem;font-weight:400;color:{text_secondary};"
                )
            buttons.append(f'<span style="{btn_style}">{label}</span>')
        toggles_html = (
            '<div style="display:flex;gap:0.375rem;align-items:center;">'
            + "".join(buttons)
            + "</div>"
        )

    title_html = (
        f'<div style="font-family:{heading_font};font-size:1rem;'
        f'font-weight:600;color:{text_primary};line-height:1.25;">'
        f"{title}</div>"
    )
    subtitle_html = ""
    if subtitle:
        subtitle_html = (
            f'<div style="font-family:{heading_font};font-size:0.8125rem;'
            f'font-weight:400;color:{text_secondary};margin-top:0.15rem;">'
            f"{subtitle}</div>"
        )

    header_html = (
        f'<div style="display:flex;align-items:flex-start;'
        f'justify-content:space-between;margin-bottom:0.75rem;">'
        f"<div>{title_html}{subtitle_html}</div>"
        f"{toggles_html}"
        f"</div>"
    )

    card_open = (
        f'<div style="background:{surface};border:0.5px solid {border};'
        f"border-radius:{radius};padding:1rem 1.25rem;margin-bottom:1rem;\">"
        f"{header_html}"
    )
    st.markdown(card_open, unsafe_allow_html=True)

    branded_chart(fig, height=height, key=key)

    st.markdown("</div>", unsafe_allow_html=True)


def branded_donut(
    labels: list[str],
    values: list[float],
    title: str = None,
    center_text: str = None,
    height: int = 300,
    key: str = None,
) -> None:
    """
    Renders a branded donut chart (pie with hole=0.7) inside a card.

    Parameters
    ----------
    labels : list[str]
        Slice labels.
    values : list[float]
        Slice values corresponding to each label.
    title : str, optional
        Card and chart title.
    center_text : str, optional
        Text displayed in the donut hole, e.g. "$2.4M".
    height : int
        Chart height in pixels (default 300).
    key : str, optional
        Streamlit chart key for identity stability across reruns.
    """
    font_family = TYPOGRAPHY["font_family"]
    text_primary = COLORS["text_primary"]
    text_secondary = COLORS["text_secondary"]
    surface = COLORS["surface"]
    border = COLORS["border"]
    radius = BORDER_RADIUS["lg"]
    heading_font = TYPOGRAPHY["heading_font"]
    color_seq = brand_color_sequence()

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.7,
            marker=dict(colors=color_seq[: len(labels)]),
            textinfo="percent+label",
            textfont=dict(family=font_family, color=text_primary, size=12),
            hovertemplate="<b>%{label}</b><br>%{value:,.0f} (%{percent})<extra></extra>",
        )
    )

    annotations = []
    if center_text:
        annotations.append(
            dict(
                text=center_text,
                x=0.5,
                y=0.5,
                font=dict(family=font_family, size=18, color=text_primary),
                showarrow=False,
            )
        )

    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=font_family, color=text_primary, size=13),
        annotations=annotations,
        showlegend=True,
        legend=dict(
            font=dict(color=text_primary),
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
        ),
        margin=dict(l=20, r=20, t=20, b=20),
    )

    # Render inside card
    header_html = ""
    if title:
        header_html = (
            f'<div style="font-family:{heading_font};font-size:1rem;font-weight:600;'
            f'color:{text_primary};line-height:1.25;margin-bottom:0.75rem;">'
            f"{title}</div>"
        )

    card_open = (
        f'<div style="background:{surface};border:0.5px solid {border};'
        f"border-radius:{radius};padding:1rem 1.25rem;margin-bottom:1rem;\">"
        f"{header_html}"
    )
    st.markdown(card_open, unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, key=key)
    st.markdown("</div>", unsafe_allow_html=True)


def branded_altair(chart, title: str = None) -> None:
    """
    Applies RVGT brand styling to an Altair chart and renders it via st.altair_chart.

    Parameters
    ----------
    chart : altair.Chart
        An Altair chart object to brand and render.
    title : str, optional
        Chart title. Replaces any existing title on the chart.

    Raises
    ------
    ImportError
        If the ``altair`` package is not installed.
    """
    try:
        import altair as alt  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "altair is required for branded_altair(). "
            "Install it with: pip install altair"
        ) from exc

    font_family = TYPOGRAPHY["font_family"]
    text_primary = COLORS["text_primary"]
    text_secondary = COLORS["text_secondary"]
    near_white = COLORS["surface"]
    border = COLORS["border"]

    if title is not None:
        chart = chart.properties(title=title)

    styled = (
        chart.configure_axis(
            labelFont=font_family,
            titleFont=font_family,
            labelColor=text_secondary,
            titleColor=text_primary,
            gridColor=border,
            domainColor=border,
        )
        .configure_title(
            font=font_family,
            color=text_primary,
            fontSize=16,
            anchor="start",
        )
        .configure_view(
            strokeColor=border,
            fill=near_white,
        )
        .configure_range(
            category=list(CHART_PALETTE),
        )
        .configure_legend(
            labelFont=font_family,
            titleFont=font_family,
            labelColor=text_primary,
            titleColor=text_secondary,
        )
    )

    st.altair_chart(styled, use_container_width=True)


# Spec alias — branded_plotly is the canonical name in the issue spec;
# branded_chart is the implementation name. Both are exported.
branded_plotly = branded_chart
