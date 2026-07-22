"""Surface → data fetcher.

Each surface maps to one or more BFF endpoints. The fetcher calls those
endpoints internally (via the data layer, not HTTP) and returns a list of
tabular datasets ready for formatting.

Each dataset is a dict:
  { "title": "Sheet / section name",
    "columns": ["Col A", "Col B", ...],
    "rows": [[val, val, ...], ...] }
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy imports so the module loads even when optional data modules are absent
# ---------------------------------------------------------------------------


def _safe_import(module_path: str, func_name: str):
    """Return a callable or None if the import fails."""
    try:
        import importlib

        mod = importlib.import_module(module_path)
        return getattr(mod, func_name, None)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Dataset helper
# ---------------------------------------------------------------------------


@dataclass
class Dataset:
    title: str
    columns: list[str] = field(default_factory=list)
    rows: list[list] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Per-surface fetchers
# ---------------------------------------------------------------------------


def _fetch_scorecard(**_kw) -> list[Dataset]:
    fn = _safe_import("src.data.scorecard_queries", "get_kpi_summary")
    if not fn:
        return [Dataset(title="Scorecard KPIs")]
    data = fn()
    ds = Dataset(
        title="Scorecard KPIs",
        columns=["Name", "Value", "Target", "Delta", "Delta %", "Trend", "Status"],
    )
    for k in data:
        ds.rows.append([
            k.get("name", ""),
            k.get("value", 0),
            k.get("target", 0),
            k.get("delta", 0),
            k.get("delta_pct", 0),
            k.get("trend", "flat"),
            k.get("alert_status", ""),
        ])
    # Financial summary
    fn2 = _safe_import("src.data.scorecard_queries", "get_financial_summary")
    if fn2:
        fdata = fn2()
        ds2 = Dataset(
            title="Financial Summary",
            columns=["Label", "Value", "Delta", "Format"],
        )
        for m in fdata:
            ds2.rows.append([
                m.get("label", ""),
                m.get("value", 0),
                m.get("delta", 0),
                m.get("format", "number"),
            ])
        return [ds, ds2]
    return [ds]


def _fetch_spend(**_kw) -> list[Dataset]:
    fn_ov = _safe_import("src.data.spend_queries", "get_spend_overview")
    fn_pa = _safe_import("src.data.spend_queries", "get_spend_pacing")
    fn_dm = _safe_import("src.data.spend_queries", "get_dma_spend")
    datasets: list[Dataset] = []
    if fn_ov:
        data = fn_ov()
        ds = Dataset(title="Spend Overview", columns=["Channel", "Budget", "Spend", "Pacing %", "ROAS", "CPA"])
        for r in data:
            ds.rows.append([
                r.get("channel", ""),
                r.get("budget", 0),
                r.get("spend", 0),
                r.get("pacing_pct", 0),
                r.get("roas", 0),
                r.get("cpa", 0),
            ])
        datasets.append(ds)
    if fn_pa:
        data = fn_pa()
        ds = Dataset(title="Spend Pacing", columns=["Channel", "Budgeted", "Actual", "Variance", "Pace Status"])
        for r in data:
            ds.rows.append([
                r.get("channel", ""),
                r.get("budgeted", 0),
                r.get("actual", 0),
                r.get("variance", 0),
                r.get("pace_status", ""),
            ])
        datasets.append(ds)
    if fn_dm:
        data = fn_dm()
        ds = Dataset(title="DMA Spend", columns=["DMA", "Spend", "Households", "CPIHH", "Index"])
        for r in data:
            ds.rows.append([
                r.get("dma", r.get("name", "")),
                r.get("spend", 0),
                r.get("households", 0),
                r.get("cpihh", 0),
                r.get("index", 0),
            ])
        datasets.append(ds)
    return datasets or [Dataset(title="Spend")]


def _fetch_funnel(**_kw) -> list[Dataset]:
    fn = _safe_import("src.data.funnel_queries", "get_funnel_stages")
    if not fn:
        return [Dataset(title="Funnel Stages")]
    data = fn()
    ds = Dataset(title="Funnel Stages", columns=["Stage", "Volume", "Conversion %", "Drop-off %"])
    for r in data:
        ds.rows.append([
            r.get("stage", ""),
            r.get("volume", 0),
            r.get("conversion_rate", 0),
            r.get("dropoff_rate", 0),
        ])
    return [ds]


def _fetch_media(**_kw) -> list[Dataset]:
    fn = _safe_import("src.data.brand_media_queries", "get_brand_overview")
    if not fn:
        return [Dataset(title="Brand Media")]
    data = fn()
    ds = Dataset(title="Brand Media Overview", columns=["Metric", "Value"])
    if isinstance(data, dict):
        for k, v in data.items():
            ds.rows.append([k, v])
    elif isinstance(data, list):
        for r in data:
            ds.rows.append([r.get("metric", r.get("name", "")), r.get("value", "")])
    return [ds]


def _fetch_sem(**_kw) -> list[Dataset]:
    fn = _safe_import("src.data.sem_queries", "get_sem_overview")
    fn_kw = _safe_import("src.data.sem_queries", "get_sem_keywords")
    datasets: list[Dataset] = []
    if fn:
        data = fn()
        ds = Dataset(title="SEM Overview", columns=["Metric", "Value"])
        if isinstance(data, dict):
            for k, v in data.items():
                ds.rows.append([k, v])
        elif isinstance(data, list):
            for r in data:
                ds.rows.append([r.get("metric", r.get("name", "")), r.get("value", "")])
        datasets.append(ds)
    if fn_kw:
        data = fn_kw()
        ds = Dataset(title="SEM Keywords", columns=["Keyword", "Impressions", "Clicks", "CTR", "CPC", "Conversions"])
        for r in (data if isinstance(data, list) else []):
            ds.rows.append([
                r.get("keyword", ""),
                r.get("impressions", 0),
                r.get("clicks", 0),
                r.get("ctr", 0),
                r.get("cpc", 0),
                r.get("conversions", 0),
            ])
        datasets.append(ds)
    return datasets or [Dataset(title="SEM")]


def _fetch_seo(**_kw) -> list[Dataset]:
    fn = _safe_import("src.data.seo_queries", "get_seo_rankings")
    if not fn:
        return [Dataset(title="SEO Rankings")]
    data = fn()
    ds = Dataset(title="SEO Rankings", columns=["Keyword", "Position", "Change", "Volume", "URL"])
    for r in (data if isinstance(data, list) else []):
        ds.rows.append([
            r.get("keyword", ""),
            r.get("position", 0),
            r.get("change", 0),
            r.get("volume", 0),
            r.get("url", ""),
        ])
    return [ds]


def _fetch_aeo(**_kw) -> list[Dataset]:
    fn = _safe_import("src.data.aeo_queries", "get_aeo_summary")
    if not fn:
        return [Dataset(title="AEO Summary")]
    data = fn()
    ds = Dataset(title="AEO Summary", columns=["Metric", "Value"])
    if isinstance(data, dict):
        for k, v in data.items():
            ds.rows.append([k, v])
    elif isinstance(data, list):
        for r in data:
            ds.rows.append([r.get("metric", r.get("name", "")), r.get("value", "")])
    return [ds]


def _fetch_social(**_kw) -> list[Dataset]:
    fn = _safe_import("src.data.social_queries", "get_social_overview")
    fn_p = _safe_import("src.data.social_queries", "get_social_platforms")
    datasets: list[Dataset] = []
    if fn:
        data = fn()
        ds = Dataset(title="Social Overview", columns=["Metric", "Value"])
        if isinstance(data, dict):
            for k, v in data.items():
                ds.rows.append([k, v])
        elif isinstance(data, list):
            for r in data:
                ds.rows.append([r.get("metric", r.get("name", "")), r.get("value", "")])
        datasets.append(ds)
    if fn_p:
        data = fn_p()
        ds = Dataset(title="Social Platforms", columns=["Platform", "Followers", "Engagement", "Posts"])
        for r in (data if isinstance(data, list) else []):
            ds.rows.append([
                r.get("platform", ""),
                r.get("followers", 0),
                r.get("engagement_rate", r.get("engagement", 0)),
                r.get("posts", 0),
            ])
        datasets.append(ds)
    return datasets or [Dataset(title="Social")]


def _fetch_awareness(**_kw) -> list[Dataset]:
    fn = _safe_import("src.data.brand_awareness_queries", "get_share_of_search")
    fn_p = _safe_import("src.data.brand_awareness_queries", "get_peer_comparison")
    datasets: list[Dataset] = []
    if fn:
        data = fn()
        ds = Dataset(title="Share of Search", columns=["Brand", "Share %", "Trend"])
        for r in (data if isinstance(data, list) else []):
            ds.rows.append([
                r.get("brand", r.get("name", "")),
                r.get("share", r.get("share_pct", 0)),
                r.get("trend", ""),
            ])
        datasets.append(ds)
    if fn_p:
        data = fn_p()
        ds = Dataset(title="Peer Comparison", columns=["Bank", "Score", "Rank"])
        for r in (data if isinstance(data, list) else []):
            ds.rows.append([
                r.get("bank", r.get("name", "")),
                r.get("score", 0),
                r.get("rank", 0),
            ])
        datasets.append(ds)
    return datasets or [Dataset(title="Brand Awareness")]


def _fetch_product(**_kw) -> list[Dataset]:
    fn = _safe_import("src.data.product_queries", "get_pipeline")
    fn_r = _safe_import("src.data.product_queries", "get_roadmap")
    fn_t = _safe_import("src.data.product_queries", "get_testing_velocity")
    datasets: list[Dataset] = []
    if fn:
        data = fn()
        ds = Dataset(title="Product Pipeline", columns=["Name", "Stage", "Product", "Launch Date", "Status"])
        for r in (data if isinstance(data, list) else []):
            ds.rows.append([
                r.get("name", ""),
                r.get("stage", ""),
                r.get("product", ""),
                r.get("launch_date", ""),
                r.get("status", ""),
            ])
        datasets.append(ds)
    if fn_t:
        data = fn_t()
        ds = Dataset(title="Testing Velocity", columns=["Name", "Variant", "Lift %", "Confidence", "Status"])
        for r in (data if isinstance(data, list) else []):
            ds.rows.append([
                r.get("name", ""),
                r.get("variant", ""),
                r.get("lift_pct", r.get("lift", 0)),
                r.get("confidence", 0),
                r.get("status", ""),
            ])
        datasets.append(ds)
    return datasets or [Dataset(title="Product")]


def _fetch_retention(**_kw) -> list[Dataset]:
    fn = _safe_import("src.data.retention_queries", "get_retention_curves")
    fn_k = _safe_import("src.data.retention_queries", "get_retention_kpis")
    datasets: list[Dataset] = []
    if fn_k:
        data = fn_k()
        ds = Dataset(title="Retention KPIs", columns=["Metric", "Value", "Target", "Trend"])
        for r in (data if isinstance(data, list) else []):
            ds.rows.append([
                r.get("name", r.get("metric", "")),
                r.get("value", 0),
                r.get("target", 0),
                r.get("trend", ""),
            ])
        datasets.append(ds)
    if fn:
        data = fn()
        ds = Dataset(title="Retention Curves", columns=["Product", "MOB", "Retained %"])
        for r in (data if isinstance(data, list) else []):
            product = r.get("product", "")
            for pt in r.get("points", r.get("curve", [])):
                if isinstance(pt, dict):
                    ds.rows.append([product, pt.get("mob", 0), pt.get("retained", pt.get("rate", 0))])
        datasets.append(ds)
    return datasets or [Dataset(title="Retention")]


def _fetch_operations(**_kw) -> list[Dataset]:
    fn = _safe_import("src.data.ops_queries", "get_approvals")
    fn_h = _safe_import("src.data.ops_queries", "get_health_metrics")
    datasets: list[Dataset] = []
    if fn:
        data = fn()
        ds = Dataset(title="Approval Queue", columns=["Title", "Type", "Status", "Priority", "Submitted", "Agent"])
        items = data if isinstance(data, list) else data.get("items", []) if isinstance(data, dict) else []
        for r in items:
            ds.rows.append([
                r.get("title", ""),
                r.get("type", ""),
                r.get("status", ""),
                r.get("priority", ""),
                r.get("submitted_at", r.get("submitted", "")),
                r.get("agent", ""),
            ])
        datasets.append(ds)
    if fn_h:
        data = fn_h()
        ds = Dataset(title="Operational Health", columns=["Metric", "Value", "Status"])
        for r in (data if isinstance(data, list) else []):
            ds.rows.append([
                r.get("name", r.get("metric", "")),
                r.get("value", 0),
                r.get("status", ""),
            ])
        datasets.append(ds)
    return datasets or [Dataset(title="Operations")]


# ---------------------------------------------------------------------------
# Surface registry
# ---------------------------------------------------------------------------

SURFACE_FETCHERS: dict[str, callable] = {
    "scorecard": _fetch_scorecard,
    "spend": _fetch_spend,
    "funnel": _fetch_funnel,
    "media": _fetch_media,
    "sem": _fetch_sem,
    "seo": _fetch_seo,
    "aeo": _fetch_aeo,
    "social": _fetch_social,
    "awareness": _fetch_awareness,
    "product": _fetch_product,
    "retention": _fetch_retention,
    "operations": _fetch_operations,
    # creative, simulator, modeling, settings — not exportable
}

SURFACE_LABELS: dict[str, str] = {
    "scorecard": "Executive Scorecard",
    "spend": "Spend Allocation",
    "funnel": "Conversion Funnel",
    "media": "Brand Media",
    "sem": "Performance Media (SEM)",
    "seo": "SEO",
    "aeo": "AEO",
    "social": "Social",
    "awareness": "Brand Awareness",
    "product": "Product & Conversion",
    "retention": "Retention",
    "operations": "Operations",
}


def fetch_surface_data(surface: str, **kwargs) -> list[Dataset]:
    """Fetch tabular data for a surface. Returns list of Dataset objects."""
    fetcher = SURFACE_FETCHERS.get(surface)
    if not fetcher:
        raise ValueError(f"Surface '{surface}' is not exportable. Available: {sorted(SURFACE_FETCHERS.keys())}")
    try:
        datasets = fetcher(**kwargs)
    except Exception as e:
        log.exception("Error fetching data for surface %s", surface)
        datasets = [Dataset(title=f"{surface} (error)", columns=["Error"], rows=[[str(e)]])]
    return datasets
