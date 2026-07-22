"""
Metric computation engine.

Computes metric values from the DuckDB/Postgres data layer, using the
SQL expressions defined in the MetricDefinition catalog.

For metrics without SQL expressions (composite / derived), Python fallback
callables are registered here.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .definitions import METRIC_CATALOG, MetricDefinition
from .registry import registry

logger = logging.getLogger(__name__)


def compute_metric(
    metric_id: str,
    data: dict[str, Any],
    *,
    period: str = "current",
) -> Optional[dict[str, Any]]:
    """Compute a single metric from pre-aggregated data.

    Args:
        metric_id: The metric ID from the catalog.
        data: A dict of pre-aggregated values keyed by column name
              (e.g. {"spend": 1_200_000, "funded_accounts": 4800, ...}).
        period: "current" or "prior" — used for delta computation.

    Returns:
        {
            "id": str,
            "label": str,
            "value": float,
            "formatted": str,
            "delta": float | None,
            "delta_pct": float | None,
            "alert_level": str | None,
            "direction": str,
        }
    """
    defn = registry.get(metric_id)
    if defn is None:
        logger.warning("Unknown metric: %s", metric_id)
        return None

    value = _evaluate(defn, data)
    if value is None:
        return None

    formatted = registry.format_value(metric_id, value)
    alert_level = registry.alert_level(metric_id, value)

    # Delta from prior period (if "prior_*" keys present)
    prior_value = _evaluate(defn, data, prefix="prior_") if any(
        k.startswith("prior_") for k in data
    ) else None

    delta = None
    delta_pct = None
    if prior_value is not None and prior_value != 0:
        delta = value - prior_value
        delta_pct = delta / abs(prior_value)

    return {
        "id": defn.id,
        "label": defn.display_label,
        "value": round(value, defn.decimal_places + 2),
        "formatted": formatted,
        "delta": round(delta, 4) if delta is not None else None,
        "delta_pct": round(delta_pct, 4) if delta_pct is not None else None,
        "delta_color": registry.delta_color(metric_id, delta or 0),
        "alert_level": alert_level,
        "direction": defn.direction.value,
        "format_type": defn.format_type.value,
    }


def compute_all(
    metric_ids: list[str],
    data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Compute multiple metrics from the same data dict."""
    results = []
    for mid in metric_ids:
        result = compute_metric(mid, data)
        if result is not None:
            results.append(result)
    return results


# ─── Internal evaluation ─────────────────────────────────────────────

# Mapping from SQL aggregate fragments to Python data-key lookups
_PYTHON_EVALUATORS: dict[str, callable] = {}


def _evaluate(
    defn: MetricDefinition,
    data: dict[str, Any],
    prefix: str = "",
) -> Optional[float]:
    """Evaluate a metric from a data dict.

    For simple metrics the data dict should contain a key matching the
    metric id (e.g. data["roas"] = 3.5).  For computed metrics we use
    the registered Python evaluator.
    """
    # Direct value in data
    key = f"{prefix}{defn.id}"
    if key in data:
        v = data[key]
        return float(v) if v is not None else None

    # Registered Python evaluator
    if defn.id in _PYTHON_EVALUATORS:
        try:
            return _PYTHON_EVALUATORS[defn.id](data, prefix)
        except Exception as exc:
            logger.warning("Evaluator for %s failed: %s", defn.id, exc)
            return None

    # Fallback: try common patterns
    return _fallback_evaluate(defn, data, prefix)


def _fallback_evaluate(
    defn: MetricDefinition,
    data: dict[str, Any],
    prefix: str = "",
) -> Optional[float]:
    """Attempt to compute derived metrics from component values."""

    def _get(key: str) -> Optional[float]:
        v = data.get(f"{prefix}{key}")
        return float(v) if v is not None else None

    # ROAS = revenue / spend
    if defn.id == "roas":
        rev = _get("attributed_revenue") or _get("revenue")
        spend = _get("spend") or _get("total_spend")
        if rev is not None and spend and spend > 0:
            return rev / spend

    # CPL = spend / leads
    if defn.id == "cpl":
        spend = _get("spend") or _get("total_spend")
        leads = _get("leads")
        if spend is not None and leads and leads > 0:
            return spend / leads

    # CPIHH = spend / funded
    if defn.id == "cpihh":
        spend = _get("spend") or _get("total_spend")
        funded = _get("funded_accounts") or _get("funded")
        if spend is not None and funded and funded > 0:
            return spend / funded

    # CTR = clicks / impressions
    if defn.id == "ctr":
        clicks = _get("clicks")
        imps = _get("impressions")
        if clicks is not None and imps and imps > 0:
            return clicks / imps

    # CVR = conversions / clicks
    if defn.id == "cvr":
        convs = _get("conversions") or _get("funded")
        clicks = _get("clicks")
        if convs is not None and clicks and clicks > 0:
            return convs / clicks

    return None
