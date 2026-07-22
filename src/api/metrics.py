"""
BFF router: /api/metrics — exposes the Metric Layer catalog and computation.

Endpoints:
  GET  /api/metrics/catalog        — full metric catalog with definitions
  GET  /api/metrics/catalog/{id}   — single metric definition
  GET  /api/metrics/domains        — list of metric domains
  GET  /api/metrics/tags           — list of metric tags
"""

from fastapi import APIRouter, HTTPException

from ..metric_layer import registry

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/catalog")
def get_catalog(domain: str | None = None, tag: str | None = None):
    """Return the full metric catalog, optionally filtered."""
    if domain:
        metrics = registry.list_by_domain(domain)
    elif tag:
        metrics = registry.list_by_tag(tag)
    else:
        metrics = registry.all()

    return {
        "metrics": [
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
            }
            for m in metrics
        ],
        "count": len(metrics),
    }


@router.get("/catalog/{metric_id}")
def get_metric_definition(metric_id: str):
    """Return a single metric definition."""
    defn = registry.get(metric_id)
    if defn is None:
        raise HTTPException(status_code=404, detail=f"Metric '{metric_id}' not found")
    return {
        "id": defn.id,
        "label": defn.display_label,
        "description": defn.description,
        "format": defn.format_type.value,
        "grain": defn.grain.value,
        "direction": defn.direction.value,
        "domain": defn.domain,
        "unit": defn.unit,
        "decimal_places": defn.decimal_places,
        "tags": list(defn.tags),
        "threshold": {
            "warning_low": defn.threshold.warning_low,
            "warning_high": defn.threshold.warning_high,
            "critical_low": defn.threshold.critical_low,
            "critical_high": defn.threshold.critical_high,
        },
    }


@router.get("/domains")
def list_domains():
    """List all unique metric domains."""
    domains = sorted({m.domain for m in registry.all()})
    return {"domains": domains}


@router.get("/tags")
def list_tags():
    """List all unique metric tags."""
    tags = sorted({t for m in registry.all() for t in m.tags})
    return {"tags": tags}
