"""
Card Container Component
------------------------
Reusable styled card wrapper with optional title, subtitle, and action buttons.
"""

from __future__ import annotations

import streamlit as st

from src.config.brand import BORDER_RADIUS, COLORS, GRADIENTS, TYPOGRAPHY


def card_container(
    title: str = None,
    subtitle: str = None,
    actions: list[dict] = None,
) -> None:
    """
    Opens a styled card wrapper.

    Must be paired with a subsequent call to ``card_container_end()``.

    Parameters
    ----------
    title : str, optional
        Card heading rendered in brand heading font.
    subtitle : str, optional
        Secondary description rendered below the title in smaller, muted text.
    actions : list[dict], optional
        Pill-style toggle buttons rendered on the right side of the header row.
        Each dict should have ``"label": str`` and optionally ``"active": bool``.
        Example: ``[{"label": "Monthly", "active": True}, {"label": "Weekly"}]``
    """
    heading_font = TYPOGRAPHY["heading_font"]
    text_primary = COLORS["text_primary"]
    text_secondary = COLORS["text_secondary"]
    secondary = COLORS["secondary"]  # blue accent for active pills
    glass_bg = COLORS["glass_bg"]
    glass_border = COLORS["glass_border"]
    radius = BORDER_RADIUS["xl"]

    header_html = ""
    if title or actions:
        action_buttons_html = ""
        if actions:
            buttons = []
            for action in actions:
                label = action.get("label", "")
                active = action.get("active", False)
                if active:
                    btn_style = (
                        f"display:inline-flex;align-items:center;padding:3px 10px;"
                        f"border-radius:9999px;border:none;"
                        f"background:{GRADIENTS['blue_cyan']};font-family:{heading_font};"
                        f"font-size:0.75rem;font-weight:600;color:#FFFFFF;cursor:pointer;"
                    )
                else:
                    btn_style = (
                        f"display:inline-flex;align-items:center;padding:3px 10px;"
                        f"border-radius:9999px;border:1px solid {glass_border};"
                        f"background:transparent;font-family:{heading_font};"
                        f"font-size:0.75rem;font-weight:400;color:{text_secondary};cursor:pointer;"
                    )
                buttons.append(f'<span style="{btn_style}">{label}</span>')
            action_buttons_html = (
                f'<div style="display:flex;gap:0.375rem;align-items:center;">'
                + "".join(buttons)
                + "</div>"
            )

        title_html = ""
        if title:
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
            f'<div>{title_html}{subtitle_html}</div>'
            f'{action_buttons_html}'
            f"</div>"
        )

    html = (
        f'<div style="'
        f"background:{glass_bg};"
        f"border:1px solid {glass_border};"
        f"border-radius:{radius};"
        f"padding:1rem 1.25rem;"
        f"margin-bottom:1rem;"
        f"backdrop-filter:blur(12px);"
        f'-webkit-backdrop-filter:blur(12px);">'
        f"{header_html}"
    )

    st.markdown(html, unsafe_allow_html=True)


def card_container_end() -> None:
    """Closes the card wrapper opened by ``card_container()``."""
    st.markdown("</div>", unsafe_allow_html=True)
