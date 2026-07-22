"""
MetricRegistry — the lookup and query interface over the metric catalog.

Provides:
  - get(metric_id) → MetricDefinition
  - list_by_domain(domain) → list
  - list_by_tag(tag) → list
  - format_value(metric_id, raw_value) → str
  - catalog_json() → serialisable dict for the /api/metrics/catalog endpoint
"""

from __future__ import annotations

from typing import Optional

from .definitions import (
    METRIC_CATALOG,
    MetricDefinition,
    MetricFormat,
    MetricDirection,
)


class MetricRegistry:
    """Singleton registry backed by METRIC_CATALOG."""

    def __init__(self) -> None:
        self._catalog = METRIC_CATALOG

    # ── Lookup ───────────────────────────────────────────────────

    def get(self, metric_id: str) -> Optional[MetricDefinition]:
        return self._catalog.get(metric_id)

    def __contains__(self, metric_id: str) -> bool:
        return metric_id in self._catalog

    def all(self) -> list[MetricDefinition]:
        return list(self._catalog.values())

    def list_by_domain(self, domain: str) -> list[MetricDefinition]:
        return [m for m in self._catalog.values() if m.domain == domain]

    def list_by_tag(self, tag: str) -> list[MetricDefinition]:
        return [m for m in self._catalog.values() if tag in m.tags]

    def list_by_tags(self, tags: list[str]) -> list[MetricDefinition]:
        tag_set = set(tags)
        return [m for m in self._catalog.values() if tag_set & set(m.tags)]

    # ── Formatting ───────────────────────────────────────────────

    def format_value(self, metric_id: str, raw: float) -> str:
        defn = self.get(metric_id)
        if defn is None:
            return str(raw)
        return _format(raw, defn)

    def delta_color(self, metric_id: str, delta: float) -> str:
        """Return 'positive' | 'negative' | 'neutral' based on direction."""
        defn = self.get(metric_id)
        if defn is None or delta == 0:
            return "neutral"
        if defn.direction == MetricDirection.HIGHER_BETTER:
            return "positive" if delta > 0 else "negative"
        if defn.direction == MetricDirection.LOWER_BETTER:
            return "positive" if delta < 0 else "negative"
        return "neutral"

    def alert_level(self, metric_id: str, value: float) -> Optional[str]:
        """Return 'critical' | 'warning' | None based on thresholds."""
        defn = self.get(metric_id)
        if defn is None:
            return None
        t = defn.threshold
        if t.critical_low is not None and value < t.critical_low:
            return "critical"
        if t.critical_high is not None and value > t.critical_high:
            return "critical"
        if t.warning_low is not None and value < t.warning_low:
            return "warning"
        if t.warning_high is not None and value > t.warning_high:
            return "warning"
        return None

    # ── Serialisation ────────────────────────────────────────────

    def catalog_json(self) -> list[dict]:
        """Return a JSON-serialisable catalog for the BFF."""
        return [
            {
                "id": m.id,
                "label": m.display_label,
                "description": m.description,
                "format": m.format_type.value,
                "grain": m.grain.value,
                "direction": m.direction.value,
                "domain": m.domain,
                "unit": m.unit,
                "tags": list(m.tags),
                "sparkline": m.sparkline_enabled,
                "has_threshold": any([
                    m.threshold.warning_low,
                    m.threshold.warning_high,
                    m.threshold.critical_low,
                    m.threshold.critical_high,
                ]),
            }
            for m in self._catalog.values()
        ]


def _format(value: float, defn: MetricDefinition) -> str:
    """Human-readable format for a metric value."""
    dp = defn.decimal_places

    if defn.format_type == MetricFormat.CURRENCY:
        if abs(value) >= 1_000_000_000:
            return f"${value / 1_000_000_000:.{dp}f}B"
        if abs(value) >= 1_000_000:
            return f"${value / 1_000_000:.{dp}f}M"
        if abs(value) >= 1_000:
            return f"${value / 1_000:.0f}k"
        return f"${value:.{dp}f}"

    if defn.format_type == MetricFormat.PERCENT:
        return f"{value * 100:.{dp}f}%"

    if defn.format_type == MetricFormat.RATIO:
        return f"{value:.{dp}f}x"

    if defn.format_type == MetricFormat.INDEX:
        return f"{value:.{dp}f}"

    if defn.format_type == MetricFormat.DURATION:
        return f"{value:.{dp}f}d"

    # NUMBER — default
    if abs(value) >= 1_000:
        return f"{value:,.0f}"
    return f"{value:.{dp}f}"


# Module-level singleton
registry = MetricRegistry()
