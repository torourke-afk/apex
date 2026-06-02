"""
QA tests for src/components/alert_badge.py (APE-35)
"""

import sys
import os
import re
import types
import pytest

# ---------------------------------------------------------------------------
# Minimal Streamlit stub so tests run without a live Streamlit session
# ---------------------------------------------------------------------------

class _MockSt:
    """Captures st.markdown calls for assertion."""
    def __init__(self):
        self.last_html = None
        self.last_kwargs = {}

    def markdown(self, html: str, **kwargs):
        self.last_html = html
        self.last_kwargs = kwargs


_mock_st = _MockSt()

# Inject stubs before importing the component
sys.modules.setdefault("streamlit", types.SimpleNamespace(markdown=_mock_st.markdown))

# Ensure src/ is on the path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Now import (using the executor's workspace path via symlink or direct import)
# We test against the executor workspace where the file lives.
EXECUTOR_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__),
                 "../../26aa10f0-519d-418d-a1cc-d66c6319f47d")
)
if EXECUTOR_ROOT not in sys.path:
    sys.path.insert(0, EXECUTOR_ROOT)

# Patch streamlit in executor context too
import importlib
st_stub = types.ModuleType("streamlit")
st_stub.markdown = _mock_st.markdown
sys.modules["streamlit"] = st_stub

from src.components.alert_badge import alert_badge, _SEVERITY_CONFIG  # noqa: E402
from src.config.brand import COLORS  # noqa: E402


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _capture(text: str, severity: str) -> str:
    _mock_st.last_html = None
    alert_badge(text, severity)
    return _mock_st.last_html


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSeverityColors:
    """Each severity maps to the correct brand color and has no hardcoded hex."""

    def test_info_uses_iron_color(self):
        """APE-55 changed info severity from primary (red) to iron (gray)."""
        html = _capture("Test", "info")
        assert COLORS["iron"] in html, "info bg should be brand iron (gray)"

    def test_success_uses_success_color(self):
        html = _capture("Test", "success")
        assert COLORS["success"] in html, "success bg should be brand success"

    def test_warning_uses_warning_color(self):
        html = _capture("Test", "warning")
        assert COLORS["warning"] in html, "warning bg should be brand warning"

    def test_error_uses_error_color(self):
        html = _capture("Test", "error")
        assert COLORS["error"] in html, "error bg should be brand error"


class TestNoPureBlackOrWhite:
    """No severity badge may contain #000000 or #FFFFFF."""

    @pytest.mark.parametrize("severity", ["info", "success", "warning", "error"])
    def test_no_pure_black(self, severity):
        html = _capture("X", severity)
        assert "#000000" not in html.lower(), f"{severity} contains pure black"

    @pytest.mark.parametrize("severity", ["info", "success", "warning", "error"])
    def test_no_pure_white(self, severity):
        html = _capture("X", severity)
        assert "#ffffff" not in html.lower(), f"{severity} contains pure white"


class TestPillShape:
    """Badge must use border-radius: 9999px for pill shape."""

    @pytest.mark.parametrize("severity", ["info", "success", "warning", "error"])
    def test_pill_border_radius(self, severity):
        html = _capture("X", severity)
        assert "border-radius: 9999px" in html, f"{severity} missing pill border-radius"


class TestInlineDisplay:
    """Badge must be inline (not block) for inline text flow."""

    @pytest.mark.parametrize("severity", ["info", "success", "warning", "error"])
    def test_inline_flex(self, severity):
        html = _capture("X", severity)
        assert "inline-flex" in html, f"{severity} is not inline-flex"

    @pytest.mark.parametrize("severity", ["info", "success", "warning", "error"])
    def test_vertical_align(self, severity):
        html = _capture("X", severity)
        assert "vertical-align" in html, f"{severity} missing vertical-align"


class TestUnicodeIcons:
    """Each severity must include a unicode icon."""

    EXPECTED_ICONS = {
        "info": "●",
        "success": "▲",
        "warning": "⚠",
        "error": "▼",
    }

    @pytest.mark.parametrize("severity,icon", EXPECTED_ICONS.items())
    def test_icon_present(self, severity, icon):
        html = _capture("Badge", severity)
        assert icon in html, f"{severity} missing expected icon {icon!r}"


class TestTextRendering:
    """Text must appear in the rendered HTML."""

    def test_text_appears_in_output(self):
        html = _capture("Revenue Alert", "warning")
        assert "Revenue Alert" in html

    def test_empty_string_renders(self):
        html = _capture("", "info")
        assert html is not None


class TestUnsafeAllowHtml:
    """Must use unsafe_allow_html=True."""

    @pytest.mark.parametrize("severity", ["info", "success", "warning", "error"])
    def test_unsafe_allow_html(self, severity):
        _capture("X", severity)
        assert _mock_st.last_kwargs.get("unsafe_allow_html") is True, (
            f"{severity}: unsafe_allow_html not True"
        )


class TestInvalidSeverity:
    """Invalid severity must raise ValueError."""

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Invalid severity"):
            alert_badge("X", "critical")

    def test_empty_severity_raises(self):
        with pytest.raises(ValueError):
            alert_badge("X", "")


class TestColorsFromBrand:
    """Verify _SEVERITY_CONFIG only references keys that exist in COLORS."""

    def test_all_bg_keys_in_colors(self):
        # The component uses COLORS[key] at module load time; this validates indirectly.
        # Direct check: confirm no raw hex appears in the config values.
        for sev, cfg in _SEVERITY_CONFIG.items():
            bg = cfg["bg"]
            text = cfg["text"]
            # Values should be hex strings from COLORS — ensure they're in COLORS.values()
            assert bg in COLORS.values(), (
                f"{sev} bg color {bg!r} is not from brand COLORS"
            )
            assert text in COLORS.values(), (
                f"{sev} text color {text!r} is not from brand COLORS"
            )
