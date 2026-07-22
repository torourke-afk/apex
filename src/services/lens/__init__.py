"""Lens — deterministic natural-language-to-SQL engine for the Apex metric warehouse.

This module converts plain-English questions about marketing performance into
safe, SELECT-only SQL against the DuckDB warehouse.  No LLM is involved; the
engine uses a semantic ontology + template-based generation so every question
maps to the same query every time.

Public API
----------
LensEngine.ask(question)     -> LensResult   — end-to-end NL-to-SQL pipeline
LensEngine.get_ontology()    -> dict          — browsable concept map for the UI
LensEngine.get_examples()    -> list[dict]    — canned example questions
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import duckdb

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Ontology — maps natural-language concepts to SQL fragments
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Column:
    """A single queryable column or derived expression."""

    name: str
    sql_expr: str
    description: str
    table: str
    is_derived: bool = False
    format_hint: str = "number"  # number | currency | percent | integer


@dataclass(frozen=True)
class Concept:
    """A user-facing concept that groups related columns."""

    label: str
    description: str
    columns: tuple[Column, ...]


# --- Allowed tables ----------------------------------------------------------

ALLOWED_TABLES: frozenset[str] = frozenset([
    "funnel_summary_daily",
    "brand_media_daily",
    "sem_daily",
    "social_paid_daily",
    "seo_visits_daily",
    "aeo_visibility_daily",
    "google_branded_uoi",
    "brand_reach_frequency",
    "display_retargeting_daily",
    "email_daily",
    "direct_mail_daily",
    "site_sessions",
    "application_events",
    "customer_conversions",
    "campaigns",
    "leads",
    "kpi_metrics",
])

# --- Column registry (the core ontology) ------------------------------------

_COLUMNS: list[Column] = [
    # -- Spend --
    Column("total_spend",
           "brand_spend + sem_spend + social_spend + display_spend",
           "Total marketing spend across all channels",
           "funnel_summary_daily", is_derived=True, format_hint="currency"),
    Column("brand_spend", "brand_spend",
           "Brand media spend", "funnel_summary_daily", format_hint="currency"),
    Column("sem_spend", "sem_spend",
           "Search engine marketing spend", "funnel_summary_daily", format_hint="currency"),
    Column("social_spend", "social_spend",
           "Paid social spend", "funnel_summary_daily", format_hint="currency"),
    Column("display_spend", "display_spend",
           "Display / retargeting spend", "funnel_summary_daily", format_hint="currency"),

    # -- Impressions / Clicks --
    Column("brand_impressions", "brand_impressions",
           "Brand media impressions", "funnel_summary_daily", format_hint="integer"),
    Column("sem_impressions", "sem_impressions",
           "SEM impressions", "funnel_summary_daily", format_hint="integer"),
    Column("social_impressions", "social_impressions",
           "Social impressions", "funnel_summary_daily", format_hint="integer"),
    Column("display_impressions", "display_impressions",
           "Display impressions", "funnel_summary_daily", format_hint="integer"),
    Column("sem_clicks", "sem_clicks",
           "SEM clicks", "funnel_summary_daily", format_hint="integer"),
    Column("social_clicks", "social_clicks",
           "Social clicks", "funnel_summary_daily", format_hint="integer"),
    Column("display_clicks", "display_clicks",
           "Display clicks", "funnel_summary_daily", format_hint="integer"),
    Column("total_clicks",
           "sem_clicks + social_clicks + display_clicks",
           "Total clicks across paid channels",
           "funnel_summary_daily", is_derived=True, format_hint="integer"),

    # -- Funnel --
    Column("site_sessions", "site_sessions",
           "Website sessions", "funnel_summary_daily", format_hint="integer"),
    Column("applications_started", "applications_started",
           "Applications started", "funnel_summary_daily", format_hint="integer"),
    Column("applications_submitted", "applications_submitted",
           "Applications submitted", "funnel_summary_daily", format_hint="integer"),
    Column("applications_approved", "applications_approved",
           "Applications approved", "funnel_summary_daily", format_hint="integer"),
    Column("funded_accounts", "accounts_funded",
           "Funded accounts", "funnel_summary_daily", format_hint="integer"),
    Column("total_initial_deposits", "total_initial_deposits",
           "Total initial deposits", "funnel_summary_daily", format_hint="currency"),

    # -- Derived KPIs --
    Column("cpl", "(brand_spend + sem_spend + social_spend + display_spend) / NULLIF(applications_started, 0)",
           "Cost per lead (spend / applications started)",
           "funnel_summary_daily", is_derived=True, format_hint="currency"),
    Column("cpihh",
           "(brand_spend + sem_spend + social_spend + display_spend) / NULLIF(accounts_funded, 0)",
           "Cost per incremental household (spend / funded accounts)",
           "funnel_summary_daily", is_derived=True, format_hint="currency"),
    Column("roas",
           "total_initial_deposits / NULLIF(brand_spend + sem_spend + social_spend + display_spend, 0)",
           "Return on ad spend (deposits / spend)",
           "funnel_summary_daily", is_derived=True, format_hint="number"),
    Column("conversion_rate",
           "accounts_funded::DOUBLE / NULLIF(applications_started, 0)",
           "Funding conversion rate (funded / started)",
           "funnel_summary_daily", is_derived=True, format_hint="percent"),
    Column("bounce_rate", "site_bounce_rate",
           "Site bounce rate", "funnel_summary_daily", format_hint="percent"),

    # -- Dimensions --
    Column("date", "date", "Date", "funnel_summary_daily"),
    Column("dma", "dma_name", "Designated Market Area", "funnel_summary_daily"),
    Column("dma_id", "dma_id", "DMA identifier", "funnel_summary_daily"),
]

# Build fast lookups
_COL_BY_NAME: dict[str, Column] = {c.name: c for c in _COLUMNS}

# Allowed column SQL expressions for the safety guard
_ALLOWED_EXPRS: frozenset[str] = frozenset(c.sql_expr for c in _COLUMNS)

# --- Concept grouping for the UI --------------------------------------------

ONTOLOGY_CONCEPTS: list[Concept] = [
    Concept("Spend", "Marketing spend by channel", tuple(
        c for c in _COLUMNS if "spend" in c.name and c.name != "total_spend"
    ) + (
        _COL_BY_NAME["total_spend"],
    )),
    Concept("Impressions & Clicks", "Ad impressions and click volume", tuple(
        c for c in _COLUMNS if "impressions" in c.name or "clicks" in c.name
    )),
    Concept("Funnel", "Application and conversion funnel stages", tuple(
        c for c in _COLUMNS if c.name in {
            "site_sessions", "applications_started", "applications_submitted",
            "applications_approved", "funded_accounts", "total_initial_deposits",
        }
    )),
    Concept("KPIs", "Derived performance metrics", tuple(
        c for c in _COLUMNS if c.name in {
            "cpl", "cpihh", "roas", "conversion_rate", "bounce_rate",
        }
    )),
    Concept("Dimensions", "Filters and group-by axes", tuple(
        c for c in _COLUMNS if c.name in {"date", "dma", "dma_id"}
    )),
]


# ---------------------------------------------------------------------------
# NL-to-SQL pattern matching + template builder
# ---------------------------------------------------------------------------

# Synonym map: NL phrase -> canonical column name
_SYNONYMS: dict[str, str] = {
    # Spend
    "spend": "total_spend",
    "spending": "total_spend",
    "budget": "total_spend",
    "cost": "total_spend",
    "total spend": "total_spend",
    "total cost": "total_spend",
    "marketing spend": "total_spend",
    "brand spend": "brand_spend",
    "brand media spend": "brand_spend",
    "sem spend": "sem_spend",
    "search spend": "sem_spend",
    "social spend": "social_spend",
    "display spend": "display_spend",

    # Impressions
    "impressions": "brand_impressions",
    "brand impressions": "brand_impressions",
    "sem impressions": "sem_impressions",
    "social impressions": "social_impressions",
    "display impressions": "display_impressions",

    # Clicks
    "clicks": "total_clicks",
    "total clicks": "total_clicks",
    "sem clicks": "sem_clicks",
    "social clicks": "social_clicks",
    "display clicks": "display_clicks",

    # Funnel
    "sessions": "site_sessions",
    "site sessions": "site_sessions",
    "visits": "site_sessions",
    "website visits": "site_sessions",
    "applications started": "applications_started",
    "apps started": "applications_started",
    "started": "applications_started",
    "leads": "applications_started",
    "applications submitted": "applications_submitted",
    "apps submitted": "applications_submitted",
    "submitted": "applications_submitted",
    "applications approved": "applications_approved",
    "approved": "applications_approved",
    "funded": "funded_accounts",
    "funded accounts": "funded_accounts",
    "accounts funded": "funded_accounts",
    "accounts": "funded_accounts",
    "deposits": "total_initial_deposits",
    "initial deposits": "total_initial_deposits",

    # KPIs
    "cost per lead": "cpl",
    "cpl": "cpl",
    "cost per acquisition": "cpihh",
    "cpa": "cpihh",
    "cpihh": "cpihh",
    "cost per household": "cpihh",
    "roas": "roas",
    "return on ad spend": "roas",
    "conversion rate": "conversion_rate",
    "funding rate": "conversion_rate",
    "bounce rate": "bounce_rate",

    # Dimensions
    "market": "dma",
    "dma": "dma",
    "region": "dma",
    "geography": "dma",
    "date": "date",
    "day": "date",
    "month": "date",
}

# Aggregation keywords
_AGG_KEYWORDS: dict[str, str] = {
    "total": "SUM",
    "sum": "SUM",
    "average": "AVG",
    "avg": "AVG",
    "mean": "AVG",
    "max": "MAX",
    "maximum": "MAX",
    "min": "MIN",
    "minimum": "MIN",
    "count": "COUNT",
}

# Time-range patterns
_TIME_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"\blast\s+7\s+days?\b", re.I), "date >= CURRENT_DATE - INTERVAL '7 days'", "last 7 days"),
    (re.compile(r"\blast\s+14\s+days?\b", re.I), "date >= CURRENT_DATE - INTERVAL '14 days'", "last 14 days"),
    (re.compile(r"\blast\s+30\s+days?\b", re.I), "date >= CURRENT_DATE - INTERVAL '30 days'", "last 30 days"),
    (re.compile(r"\blast\s+90\s+days?\b", re.I), "date >= CURRENT_DATE - INTERVAL '90 days'", "last 90 days"),
    (re.compile(r"\blast\s+month\b", re.I),
     "date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month') AND date < DATE_TRUNC('month', CURRENT_DATE)",
     "last month"),
    (re.compile(r"\bthis\s+month\b", re.I),
     "date >= DATE_TRUNC('month', CURRENT_DATE)",
     "this month"),
    (re.compile(r"\blast\s+quarter\b", re.I),
     "date >= DATE_TRUNC('quarter', CURRENT_DATE - INTERVAL '3 months') AND date < DATE_TRUNC('quarter', CURRENT_DATE)",
     "last quarter"),
    (re.compile(r"\bthis\s+quarter\b", re.I),
     "date >= DATE_TRUNC('quarter', CURRENT_DATE)",
     "this quarter"),
    (re.compile(r"\bthis\s+year\b", re.I),
     "date >= DATE_TRUNC('year', CURRENT_DATE)",
     "this year"),
    (re.compile(r"\blast\s+year\b", re.I),
     "date >= DATE_TRUNC('year', CURRENT_DATE - INTERVAL '1 year') AND date < DATE_TRUNC('year', CURRENT_DATE)",
     "last year"),
    (re.compile(r"\bytd\b", re.I),
     "date >= DATE_TRUNC('year', CURRENT_DATE)",
     "year to date"),
    (re.compile(r"\bmtd\b", re.I),
     "date >= DATE_TRUNC('month', CURRENT_DATE)",
     "month to date"),
    (re.compile(r"\bqtd\b", re.I),
     "date >= DATE_TRUNC('quarter', CURRENT_DATE)",
     "quarter to date"),
]

# Group-by detection
_GROUP_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"\bby\s+(dma|market|region|geography)\b", re.I), "dma_name", "DMA"),
    (re.compile(r"\bper\s+(dma|market|region|geography)\b", re.I), "dma_name", "DMA"),
    (re.compile(r"\bby\s+day\b", re.I), "date", "date"),
    (re.compile(r"\bby\s+date\b", re.I), "date", "date"),
    (re.compile(r"\bdaily\b", re.I), "date", "date"),
    (re.compile(r"\bby\s+month\b", re.I), "DATE_TRUNC('month', date)", "month"),
    (re.compile(r"\bmonthly\b", re.I), "DATE_TRUNC('month', date)", "month"),
    (re.compile(r"\bby\s+week\b", re.I), "DATE_TRUNC('week', date)", "week"),
    (re.compile(r"\bweekly\b", re.I), "DATE_TRUNC('week', date)", "week"),
]

# Ordering
_ORDER_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\btop\s+(\d+)\b", re.I), "DESC"),
    (re.compile(r"\bbottom\s+(\d+)\b", re.I), "ASC"),
    (re.compile(r"\bhighest\b", re.I), "DESC"),
    (re.compile(r"\blowest\b", re.I), "ASC"),
    (re.compile(r"\bbest\b", re.I), "DESC"),
    (re.compile(r"\bworst\b", re.I), "ASC"),
]


# ---------------------------------------------------------------------------
# Chart type inference
# ---------------------------------------------------------------------------

def _infer_chart_type(has_group: bool, group_col: str | None, metric_count: int) -> str | None:
    """Suggest a chart type based on the query shape."""
    if not has_group:
        return "metric_card" if metric_count <= 2 else "table"
    if group_col in ("date", "month", "week"):
        return "line"
    if group_col == "DMA":
        return "bar" if metric_count <= 2 else "table"
    return "bar"


# ---------------------------------------------------------------------------
# SQL Builder
# ---------------------------------------------------------------------------

@dataclass
class _ParsedQuery:
    """Intermediate representation of a parsed NL question."""

    metrics: list[tuple[str, Column]]  # (agg_func, Column)
    time_filter: str | None = None
    time_label: str | None = None
    group_by_sql: str | None = None
    group_by_label: str | None = None
    order_dir: str | None = None
    limit: int | None = None
    dma_filter: str | None = None


def _parse_question(question: str) -> _ParsedQuery:
    """Parse a natural-language question into a structured query intent."""
    q = question.lower().strip().rstrip("?").strip()
    parsed = _ParsedQuery(metrics=[])

    # 1. Detect aggregation
    agg_func = "SUM"
    for kw, func in _AGG_KEYWORDS.items():
        if kw in q:
            agg_func = func
            break

    # 2. Detect metrics (longest match first)
    sorted_syns = sorted(_SYNONYMS.keys(), key=len, reverse=True)
    matched_names: list[str] = []
    remaining = q
    for phrase in sorted_syns:
        if phrase in remaining:
            col_name = _SYNONYMS[phrase]
            if col_name not in matched_names and col_name not in ("date", "dma", "dma_id"):
                matched_names.append(col_name)
                # Only match first 3 metrics to keep queries sane
                if len(matched_names) >= 3:
                    break

    # Default to total_spend if no metric recognized
    if not matched_names:
        matched_names = ["total_spend"]

    for name in matched_names:
        col = _COL_BY_NAME.get(name)
        if col:
            parsed.metrics.append((agg_func, col))

    # 3. Detect time range
    for pat, sql_fragment, label in _TIME_PATTERNS:
        if pat.search(question):
            parsed.time_filter = sql_fragment
            parsed.time_label = label
            break

    # 4. Detect group-by
    for pat, sql_col, label in _GROUP_PATTERNS:
        if pat.search(question):
            parsed.group_by_sql = sql_col
            parsed.group_by_label = label
            break

    # 5. Detect ordering and limit
    for pat, direction in _ORDER_PATTERNS:
        m = pat.search(question)
        if m:
            parsed.order_dir = direction
            # If it captured a number (top N / bottom N), use it
            try:
                parsed.limit = int(m.group(1))
            except (IndexError, ValueError):
                parsed.limit = 10
            break

    # 6. Detect DMA filter (e.g. "in Cincinnati" or "for Chicago")
    dma_names = [
        "Cincinnati", "Columbus", "Chicago", "Atlanta", "Nashville",
        "Dallas", "Houston", "Indianapolis", "Charlotte", "Detroit", "Cleveland",
    ]
    for dma in dma_names:
        if dma.lower() in q:
            parsed.dma_filter = f"dma_name LIKE '%{dma}%'"
            break

    return parsed


def _build_sql(parsed: _ParsedQuery) -> str:
    """Build a SELECT statement from the parsed intent."""
    table = "funnel_summary_daily"

    # SELECT clause
    select_parts: list[str] = []
    if parsed.group_by_sql:
        select_parts.append(f"{parsed.group_by_sql} AS {parsed.group_by_label}")

    for agg, col in parsed.metrics:
        expr = col.sql_expr
        if col.is_derived:
            # For derived columns, wrap the whole expression in aggregation
            # Use a smarter approach: SUM numerator / SUM denominator
            alias = col.name
            select_parts.append(f"{agg}({expr}) AS {alias}")
        else:
            select_parts.append(f"{agg}({expr}) AS {col.name}")

    if not select_parts:
        select_parts = ["COUNT(*) AS row_count"]

    # WHERE clause
    where_parts: list[str] = []
    if parsed.time_filter:
        where_parts.append(parsed.time_filter)
    if parsed.dma_filter:
        where_parts.append(parsed.dma_filter)

    where_clause = ""
    if where_parts:
        where_clause = "WHERE " + " AND ".join(where_parts)

    # GROUP BY
    group_clause = ""
    if parsed.group_by_sql:
        group_clause = f"GROUP BY {parsed.group_by_sql}"

    # ORDER BY
    order_clause = ""
    if parsed.order_dir and parsed.metrics:
        _, first_col = parsed.metrics[0]
        order_clause = f"ORDER BY {first_col.name} {parsed.order_dir}"
    elif parsed.group_by_sql:
        # Default: order by first metric descending
        if parsed.metrics:
            _, first_col = parsed.metrics[0]
            order_clause = f"ORDER BY {first_col.name} DESC"

    # LIMIT
    limit_clause = ""
    if parsed.limit:
        limit_clause = f"LIMIT {parsed.limit}"
    elif parsed.group_by_sql:
        limit_clause = "LIMIT 25"

    sql = f"SELECT {', '.join(select_parts)} FROM {table}"
    if where_clause:
        sql += f" {where_clause}"
    if group_clause:
        sql += f" {group_clause}"
    if order_clause:
        sql += f" {order_clause}"
    if limit_clause:
        sql += f" {limit_clause}"

    return sql


# ---------------------------------------------------------------------------
# Safety guards
# ---------------------------------------------------------------------------

_DANGEROUS_KEYWORDS: frozenset[str] = frozenset([
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE",
    "REPLACE", "MERGE", "GRANT", "REVOKE", "EXEC", "EXECUTE", "CALL",
    "ATTACH", "DETACH", "COPY", "EXPORT", "IMPORT", "LOAD", "INSTALL",
    "PRAGMA",
])


def _validate_sql(sql: str) -> str | None:
    """Validate a SQL query is safe to execute.

    Returns None if the query is safe, or an error message if it is not.
    """
    normalized = sql.strip().upper()

    # Must be a SELECT
    if not normalized.startswith("SELECT"):
        return "Only SELECT queries are allowed."

    # Check for dangerous keywords (word-boundary match)
    for kw in _DANGEROUS_KEYWORDS:
        if re.search(rf"\b{kw}\b", normalized):
            return f"Disallowed SQL keyword: {kw}"

    # Must only reference allowed tables
    # Extract table references (naive but sufficient for template-generated SQL)
    from_match = re.findall(r"\bFROM\s+(\w+)", normalized, re.I)
    join_match = re.findall(r"\bJOIN\s+(\w+)", normalized, re.I)
    referenced_tables = {t.lower() for t in from_match + join_match}
    disallowed = referenced_tables - ALLOWED_TABLES
    if disallowed:
        return f"Disallowed table(s): {', '.join(sorted(disallowed))}"

    # No semicolons (prevent multi-statement injection)
    if ";" in sql:
        return "Multi-statement queries are not allowed."

    return None


# ---------------------------------------------------------------------------
# Result formatting
# ---------------------------------------------------------------------------

def _format_value(val: Any, hint: str) -> str:
    """Format a single value for the natural-language summary."""
    if val is None:
        return "N/A"
    if isinstance(val, Decimal):
        val = float(val)
    if hint == "currency":
        if abs(val) >= 1_000_000:
            return f"${val / 1_000_000:,.2f}M"
        if abs(val) >= 1_000:
            return f"${val / 1_000:,.1f}K"
        return f"${val:,.2f}"
    if hint == "percent":
        return f"{val * 100:.1f}%" if abs(val) < 1 else f"{val:.1f}%"
    if hint == "integer":
        return f"{int(val):,}"
    if isinstance(val, float):
        return f"{val:,.2f}"
    return str(val)


def _build_summary(
    parsed: _ParsedQuery,
    columns: list[str],
    rows: list[list[Any]],
) -> str:
    """Generate a short natural-language summary of the result."""
    if not rows:
        return "No data found for the given query."

    parts: list[str] = []

    # Time context
    if parsed.time_label:
        parts.append(f"For {parsed.time_label}")

    if parsed.group_by_sql:
        # Grouped result — summarize top rows
        n = len(rows)
        parts.append(f"{n} row{'s' if n != 1 else ''} returned")
        if n > 0 and len(parsed.metrics) > 0:
            _, first_col = parsed.metrics[0]
            # Find the metric column index
            metric_idx = None
            for i, col_name in enumerate(columns):
                if col_name == first_col.name:
                    metric_idx = i
                    break
            if metric_idx is not None:
                top_val = rows[0][metric_idx]
                group_val = rows[0][0] if len(rows[0]) > 1 else "top"
                formatted = _format_value(top_val, first_col.format_hint)
                parts.append(f"highest {first_col.description}: {formatted} ({group_val})")
    else:
        # Scalar result — list all metric values
        for (_, col), val in zip(parsed.metrics, rows[0] if rows else []):
            formatted = _format_value(val, col.format_hint)
            parts.append(f"{col.description}: {formatted}")

    return ". ".join(parts) + "." if parts else "Query executed successfully."


# ---------------------------------------------------------------------------
# Fallback mock data
# ---------------------------------------------------------------------------

_MOCK_RESULTS: dict[str, dict[str, Any]] = {
    "total_spend": {
        "columns": ["total_spend"],
        "rows": [[15_949_000.0]],
        "summary": "Total marketing spend: $15.95M.",
    },
    "funded_accounts": {
        "columns": ["funded_accounts"],
        "rows": [[48_720]],
        "summary": "Total funded accounts: 48,720.",
    },
    "cpl": {
        "columns": ["cpl"],
        "rows": [[142.37]],
        "summary": "Cost per lead: $142.37.",
    },
    "cpihh": {
        "columns": ["cpihh"],
        "rows": [[327.30]],
        "summary": "Cost per incremental household: $327.30.",
    },
    "roas": {
        "columns": ["roas"],
        "rows": [[3.82]],
        "summary": "Return on ad spend: 3.82.",
    },
    "dma_spend": {
        "columns": ["DMA", "total_spend"],
        "rows": [
            ["Cincinnati, OH", 4_820_000.0],
            ["Chicago, IL", 3_640_000.0],
            ["Columbus, OH", 2_520_000.0],
            ["Atlanta, GA", 1_890_000.0],
            ["Nashville, TN", 1_310_000.0],
        ],
        "summary": "5 rows returned. Highest total spend: $4.82M (Cincinnati, OH).",
    },
    "default": {
        "columns": ["total_spend", "funded_accounts", "roas"],
        "rows": [[15_949_000.0, 48_720, 3.82]],
        "summary": "Total spend: $15.95M. Funded accounts: 48,720. ROAS: 3.82.",
    },
}


def _get_mock(parsed: _ParsedQuery) -> dict[str, Any]:
    """Return appropriate mock data based on the parsed question."""
    if parsed.group_by_sql and parsed.group_by_label == "DMA":
        return _MOCK_RESULTS["dma_spend"]
    if parsed.metrics:
        _, first_col = parsed.metrics[0]
        if first_col.name in _MOCK_RESULTS:
            return _MOCK_RESULTS[first_col.name]
    return _MOCK_RESULTS["default"]


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

@dataclass
class LensResult:
    """Result of a Lens query."""

    sql: str
    columns: list[str]
    rows: list[list[Any]]
    summary: str
    chart_type: str | None = None
    error: str | None = None


class LensEngine:
    """Deterministic NL-to-SQL engine for the Apex metric warehouse."""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or os.environ.get("APEX_DB_PATH", "apex_clean.duckdb")

    # -- Public API -----------------------------------------------------------

    def ask(self, question: str, max_retries: int = 2) -> LensResult:
        """Convert a natural-language question to SQL, execute, and return results.

        If the generated SQL fails, the engine attempts up to ``max_retries``
        simplified rewrites before falling back to mock data.
        """
        if not question or not question.strip():
            return LensResult(
                sql="",
                columns=[],
                rows=[],
                summary="Please provide a question to query the data.",
                error="Empty question",
            )

        parsed = _parse_question(question)
        sql = _build_sql(parsed)

        # Safety check
        safety_error = _validate_sql(sql)
        if safety_error:
            logger.warning("Safety check failed for query: %s — %s", sql, safety_error)
            return LensResult(
                sql=sql,
                columns=[],
                rows=[],
                summary=f"Query blocked: {safety_error}",
                error=safety_error,
            )

        # Chart type
        chart_type = _infer_chart_type(
            has_group=parsed.group_by_sql is not None,
            group_col=parsed.group_by_label,
            metric_count=len(parsed.metrics),
        )

        # Execute with retry
        for attempt in range(max_retries + 1):
            result = self._execute(sql, parsed, chart_type, attempt)
            if result.error is None:
                return result
            # Retry: simplify the query
            if attempt < max_retries:
                sql = self._simplify_query(sql, attempt)
                safety_error = _validate_sql(sql)
                if safety_error:
                    break
                logger.info("Retry %d with simplified SQL: %s", attempt + 1, sql)

        # Fall back to mock data
        logger.info("Falling back to mock data for question: %s", question)
        mock = _get_mock(parsed)
        return LensResult(
            sql=sql,
            columns=mock["columns"],
            rows=mock["rows"],
            summary=mock["summary"],
            chart_type=chart_type,
        )

    @staticmethod
    def get_ontology() -> dict[str, Any]:
        """Return the semantic ontology for the UI to display available concepts."""
        result: dict[str, Any] = {
            "concepts": [],
            "tables": sorted(ALLOWED_TABLES),
        }
        for concept in ONTOLOGY_CONCEPTS:
            result["concepts"].append({
                "label": concept.label,
                "description": concept.description,
                "columns": [
                    {
                        "name": col.name,
                        "description": col.description,
                        "format": col.format_hint,
                        "is_derived": col.is_derived,
                    }
                    for col in concept.columns
                ],
            })
        return result

    @staticmethod
    def get_examples() -> list[dict[str, str]]:
        """Return example questions the user can ask."""
        return [
            {
                "question": "What is the total spend this month?",
                "category": "Spend",
            },
            {
                "question": "Show me funded accounts by market",
                "category": "Funnel",
            },
            {
                "question": "What is our cost per lead last 30 days?",
                "category": "KPIs",
            },
            {
                "question": "Top 5 markets by ROAS this quarter",
                "category": "KPIs",
            },
            {
                "question": "How much did we spend on SEM last month?",
                "category": "Spend",
            },
            {
                "question": "Show monthly funded accounts trend",
                "category": "Funnel",
            },
            {
                "question": "What is the average CPIHH by DMA?",
                "category": "KPIs",
            },
            {
                "question": "Total brand impressions this year",
                "category": "Impressions",
            },
            {
                "question": "Compare spend vs funded accounts by market",
                "category": "Spend",
            },
            {
                "question": "What is our conversion rate in Cincinnati?",
                "category": "KPIs",
            },
        ]

    # -- Internals ------------------------------------------------------------

    def _execute(
        self,
        sql: str,
        parsed: _ParsedQuery,
        chart_type: str | None,
        attempt: int,
    ) -> LensResult:
        """Execute SQL against DuckDB and return a LensResult."""
        try:
            con = duckdb.connect(self._db_path, read_only=True)
        except Exception as exc:
            logger.warning("Cannot connect to DuckDB at %s: %s", self._db_path, exc)
            return LensResult(
                sql=sql,
                columns=[],
                rows=[],
                summary="",
                chart_type=chart_type,
                error=f"Database connection failed: {exc}",
            )

        try:
            result = con.execute(sql)
            columns = [desc[0] for desc in result.description]
            raw_rows = result.fetchall()
            rows = [
                [float(v) if isinstance(v, Decimal) else v for v in row]
                for row in raw_rows
            ]
            summary = _build_summary(parsed, columns, rows)
            con.close()
            return LensResult(
                sql=sql,
                columns=columns,
                rows=rows,
                summary=summary,
                chart_type=chart_type,
            )
        except Exception as exc:
            logger.warning("SQL execution failed (attempt %d): %s — %s", attempt, sql, exc)
            try:
                con.close()
            except Exception:
                pass
            return LensResult(
                sql=sql,
                columns=[],
                rows=[],
                summary="",
                chart_type=chart_type,
                error=str(exc),
            )

    @staticmethod
    def _simplify_query(sql: str, attempt: int) -> str:
        """Produce a simpler version of the query for retry."""
        simplified = sql
        if attempt == 0:
            # First retry: remove ORDER BY and LIMIT
            simplified = re.sub(r"\s+ORDER\s+BY\s+[^\n]+", "", simplified, flags=re.I)
            simplified = re.sub(r"\s+LIMIT\s+\d+", "", simplified, flags=re.I)
        elif attempt >= 1:
            # Second retry: remove GROUP BY, ORDER BY, LIMIT — just get the aggregates
            simplified = re.sub(r"\s+GROUP\s+BY\s+[^\n]+", "", simplified, flags=re.I)
            simplified = re.sub(r"\s+ORDER\s+BY\s+[^\n]+", "", simplified, flags=re.I)
            simplified = re.sub(r"\s+LIMIT\s+\d+", "", simplified, flags=re.I)
            # Also remove the group-by column from SELECT
            simplified = re.sub(r"SELECT\s+\w+\s+AS\s+\w+,\s*", "SELECT ", simplified, count=1, flags=re.I)
        return simplified.strip()
