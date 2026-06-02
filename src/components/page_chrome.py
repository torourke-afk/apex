"""
Page Chrome Component
---------------------
Shared sidebar branding and page header with breadcrumb.
Call ``page_chrome()`` at the top of every page after ``set_page_config``.
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from src.config.brand import COLORS, GRADIENTS, TYPOGRAPHY, BORDER_RADIUS, inject_brand_css


def _sidebar_brand() -> None:
    """Render APEX branding in the sidebar — logo, subtitle, divider."""
    ff = TYPOGRAPHY["font_family"]
    with st.sidebar:
        st.markdown(
            f"""<div style="padding: 0.5rem 0 0.25rem;">
  <a href="/" target="_self" style="text-decoration: none; display: block;">
  <h1 style="
      color: {COLORS['text_primary']};
      font-size: 28px;
      margin: 0 0 2px 0;
      letter-spacing: -0.02em;
      font-family: {ff};
      font-weight: 800;
      cursor: pointer;
  "><span style="
      background: {GRADIENTS['blue_cyan']};
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
  ">APEX</span></h1>
  </a>
  <p style="
      color: {COLORS['text_secondary']};
      font-size: 11px;
      margin: 0;
      font-family: {ff};
      font-weight: 500;
      letter-spacing: 0.08em;
      text-transform: uppercase;
  ">RVGT · CMO Dashboard</p>
</div>""",
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<hr style="border: none; border-top: 1px solid {COLORS["glass_border"]}; '
            f'margin: 0.75rem 0;">',
            unsafe_allow_html=True,
        )


def _page_header(title: str, breadcrumb: str | None = None) -> None:
    """Render a Vision UI-style page header with breadcrumb and title."""
    ff = TYPOGRAPHY["font_family"]
    crumb = breadcrumb or f"Pages / {title}"

    st.markdown(
        f"""<div style="
    margin-bottom: 1rem;
    padding: 0.25rem 0;
">
  <p style="
      color: {COLORS['text_secondary']};
      font-family: {ff};
      font-size: 0.75rem;
      font-weight: 400;
      margin: 0 0 0.15rem 0;
      letter-spacing: 0.01em;
  ">{crumb}</p>
  <h1 style="
      color: {COLORS['text_primary']};
      font-family: {ff};
      font-size: 1.5rem;
      font-weight: 700;
      margin: 0;
      line-height: 1.25;
  ">{title}</h1>
</div>""",
        unsafe_allow_html=True,
    )


def page_chrome(
    title: str,
    breadcrumb: str | None = None,
    show_header: bool = True,
) -> None:
    """Render shared page chrome — sidebar branding + page header.

    Call this at the top of every page, right after any ``st.set_page_config``
    call (Streamlit requires that to be first).

    Parameters
    ----------
    title : str
        Page title displayed in the header and used in the breadcrumb.
    breadcrumb : str, optional
        Override the default "Pages / {title}" breadcrumb text.
    show_header : bool
        When False, only the sidebar branding is rendered (useful for the
        home/app page which has its own welcome section).
    """
    inject_brand_css()
    components.html(
        """<script>
        (function() {
          var win = window.parent;
          if (win._apexFocusPatched) return;
          win._apexFocusPatched = true;
          var _focus = win.HTMLElement.prototype.focus;
          win.HTMLElement.prototype.focus = function(opts) {
            _focus.call(this, Object.assign({preventScroll: true}, opts));
          };
        })();
        </script>""",
        height=0,
        scrolling=False,
    )
    _sidebar_brand()
    if show_header:
        _page_header(title, breadcrumb)
