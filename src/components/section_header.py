"""
Section Header Component
------------------------
Styled section heading with optional subtitle and right-aligned action link.
"""

from __future__ import annotations

import streamlit as st

from src.config.brand import COLORS, TYPOGRAPHY


def section_header(
    title: str,
    subtitle: str = None,
    icon: str = None,
    action: str = None,
) -> None:
    """
    Renders a branded section header without a divider.

    Parameters
    ----------
    title : str
        Section title rendered in brand heading font and color.
    subtitle : str, optional
        Secondary description rendered below the title in smaller, muted text.
    icon : str, optional
        Emoji or symbol rendered inline before the title text.
    action : str, optional
        Text for a right-aligned action link (e.g. "View All →").
    """
    heading_font = TYPOGRAPHY["heading_font"]
    title_size = TYPOGRAPHY["sizes"]["xl"]
    title_weight = TYPOGRAPHY["weights"]["bold"]
    text_primary = COLORS["text_primary"]
    text_secondary = COLORS["text_secondary"]
    accent = COLORS["secondary"]  # blue accent for links

    icon_html = f'<span style="margin-right: 0.4em;">{icon}</span>' if icon else ""

    action_html = ""
    if action:
        action_html = f"""<a href="#" style="
            font-family: {heading_font};
            font-size: 0.8125rem;
            font-weight: 500;
            color: {accent};
            text-decoration: none;
            white-space: nowrap;
        ">{action}</a>"""

    subtitle_html = ""
    if subtitle:
        subtitle_html = f"""
  <div style="
      font-family: {heading_font};
      font-size: 0.8125rem;
      font-weight: 400;
      color: {text_secondary};
      line-height: 1.5;
      margin-top: 0.2rem;
  ">{subtitle}</div>"""

    html = f"""
<div style="margin-bottom: 1rem;">
  <div style="display: flex; align-items: center; justify-content: space-between;">
    <div style="
        font-family: {heading_font};
        font-size: {title_size};
        font-weight: {title_weight};
        color: {text_primary};
        line-height: 1.25;
    ">{icon_html}{title}</div>
    {action_html}
  </div>{subtitle_html}
</div>
"""

    st.markdown(html, unsafe_allow_html=True)
