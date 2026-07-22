"""
Metric Layer — centralized KPI definitions for Apex.

Every KPI (CPL, ROAS, CPIHH, BEI, LLM Visibility, funnel rates, etc.) is
defined once here.  All BFF routers and services reference these definitions
instead of computing KPIs ad-hoc.

Usage:
    from src.metric_layer import registry, compute_metric
    defn = registry.get("roas")
    value = compute_metric("roas", db_session, filters)
"""

from .definitions import MetricDefinition, MetricFormat, MetricGrain, MetricDirection
from .registry import MetricRegistry, registry
from .compute import compute_metric, compute_all

__all__ = [
    "MetricDefinition",
    "MetricFormat",
    "MetricGrain",
    "MetricDirection",
    "MetricRegistry",
    "registry",
    "compute_metric",
    "compute_all",
]
