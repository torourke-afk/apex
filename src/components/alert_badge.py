"""
Alert Badge Component
---------------------
Inline colored pill/badge with icon + text for status indicators.
"""

from __future__ import annotations

import streamlit as st
from src.config.brand import COLORS

_SEVERITY_CONFIG: dict[str, dict] = {
    "info": {
        "bg": "rgba(160, 174, 192, 0.15)",   # muted glass on dark
        "text": COLORS["iron"],               # #A0AEC0
        "icon": "●",
    },
    "success": {
        "bg": "rgba(1, 181, 116, 0.15)",      # translucent green
        "text": COLORS["success"],             # #01B574
        "icon": "▲",
    },
    "warning": {
        "bg": "rgba(255, 181, 71, 0.15)",     # translucent amber
        "text": COLORS["warning"],             # #FFB547
        "icon": "⚠",
    },
    "error": {
        "bg": "rgba(227, 26, 26, 0.15)",      # translucent red
        "text": COLORS["error"],               # #E31A1A
        "icon": "▼",
    },
}


def badge_html(text: str, severity: str = "info", count: int = None) -> str:
    """Return the HTML string for a colored badge without rendering it.

    Useful for embedding a badge inside a larger HTML block (e.g. ``kpi_card``).

    Parameters
    ----------
    text : str
        Label text to display inside the badge.
    severity : str
        One of ``"info"``, ``"success"``, ``"warning"``, ``"error"``.
    count : int, optional
        When set, renders a small count bubble after the text.
    """
    if severity not in _SEVERITY_CONFIG:
        raise ValueError(
            f"Invalid severity {severity!r}. Must be one of: "
            + ", ".join(_SEVERITY_CONFIG)
        )

    cfg = _SEVERITY_CONFIG[severity]
    bg = cfg["bg"]
    color = cfg["text"]
    icon = cfg["icon"]
    ff = "'Plus Jakarta Sans', 'Inter', 'Helvetica Neue', Arial, sans-serif"

    count_html = ""
    if count is not None:
        count_html = (
            f'<span style="'
            f"display: inline-flex; align-items: center; justify-content: center;"
            f"background-color: {color}; color: {bg};"
            f"font-size: 0.65rem; font-weight: 700;"
            f"min-width: 1.2em; height: 1.2em; border-radius: 9999px;"
            f"margin-left: 0.3em; padding: 0 0.25em;"
            f'">{count}</span>'
        )

    return (
        f'<span style="'
        f"display: inline-flex; align-items: center; gap: 0.3em;"
        f"background-color: {bg}; color: {color};"
        f"font-family: {ff}; font-size: 0.75rem; font-weight: 600;"
        f"padding: 0.2em 0.65em; border-radius: 9999px;"
        f"line-height: 1.4; white-space: nowrap; vertical-align: middle;"
        f'">'
        f"{icon}&nbsp;{text}{count_html}"
        f"</span>"
    )


def alert_badge(text: str, severity: str = "info", count: int = None) -> None:
    """Renders an inline colored badge.

    Parameters
    ----------
    text : str
        Label text to display inside the badge.
    severity : str
        One of ``"info"``, ``"success"``, ``"warning"``, ``"error"``.
        Defaults to ``"info"``.
    count : int, optional
        When set, renders a small count bubble after the text.
    """
    st.markdown(badge_html(text, severity, count=count), unsafe_allow_html=True)
