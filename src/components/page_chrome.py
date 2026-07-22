"""
Page Chrome Component
---------------------
Shared page header with context bar (Signal Deck spec).
Call ``page_chrome()`` at the top of every page after ``set_page_config``.

Sidebar branding is now handled in app.py via app_chrome.render_sidebar_branding().
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from src.config.brand import inject_brand_css
from src.components.app_chrome import render_context_bar


def page_chrome(
    title: str,
    breadcrumb: str | None = None,
    show_header: bool = True,
    category: str | None = None,
) -> None:
    """Render shared page chrome — context bar with page title, sync, client, mode.

    Call this at the top of every page.

    Parameters
    ----------
    title : str
        Page title displayed in the context bar.
    breadcrumb : str, optional
        Deprecated — category is used instead. Kept for backward compatibility.
    show_header : bool
        When False, only CSS is injected (useful for the home/app page).
    category : str, optional
        Override the breadcrumb category (e.g., "COMMAND", "CHANNELS").
    """
    inject_brand_css()
    components.html("""
<script>
(function() {
  var doc = window.parent.document;
  var sel = '[data-testid="stAppScrollToBottomContainer"]';

  function lockTop(el) {
    if (el._apexLocked) return;
    el._apexLocked = true;
    var desc = Object.getOwnPropertyDescriptor(Element.prototype, 'scrollTop');
    Object.defineProperty(el, 'scrollTop', {
      get: function() { return desc.get.call(this); },
      set: function(v) {
        // Allow only explicit zero-resets; block Streamlit's scroll-to-bottom
        if (v === 0) desc.set.call(this, 0);
      },
      configurable: true
    });
    desc.set.call(el, 0);
  }

  function tryLock() {
    var el = doc.querySelector(sel);
    if (el) { lockTop(el); return true; }
    return false;
  }

  if (!tryLock()) {
    var ob = new MutationObserver(function() { if (tryLock()) ob.disconnect(); });
    ob.observe(doc.body, { childList: true, subtree: true });
  }
})();
</script>""", height=0, scrolling=False)
    if show_header:
        render_context_bar(title, category=category)
