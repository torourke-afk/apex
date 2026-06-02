"""Organic & AEO data loaders (APE-86 / APE-18c).

Read-only query functions over DuckDB organic/AEO domain tables:

    load_llm_visibility(platform, period, market)       → DataFrame
    load_competitive_aeo(competitors, period)           → DataFrame
    load_prompt_drilldown(platform, prompt_category, period) → DataFrame
    load_seo_rankings(category, period)                 → DataFrame
    load_seo_traffic(period)                            → DataFrame
    load_rank_change_alerts(threshold)                  → DataFrame

Aggregation helpers (operate on in-memory DataFrames):

    compute_mention_rate(df)                            → float
    compute_avg_position(df)                            → float
    compute_share_of_voice(df, brand)                   → float
    compute_citation_rate(df)                           → float

All loaders return typed DataFrames and handle empty results gracefully.
Connections are opened and closed per call.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from src.data.init_db import get_connection

# ---------------------------------------------------------------------------
# Valid dimension values (for input validation)
# ---------------------------------------------------------------------------

_VALID_PLATFORMS_LLM = frozenset({
    "google_ai_overviews", "chatgpt", "perplexity", "gemini", "claude", "copilot",
})

_VALID_PLATFORMS_AEO = frozenset({
    "ChatGPT", "Perplexity", "Gemini", "Claude", "Copilot", "Meta AI",
})

_VALID_CATEGORIES = frozenset({
    "checking", "savings", "mortgage", "credit_card", "auto_loan", "personal_loan",
})


# ---------------------------------------------------------------------------
# 1. load_llm_visibility
# ---------------------------------------------------------------------------


def load_llm_visibility(
    platform: Optional[str] = None,
    period: Optional[str] = None,
    market: Optional[str] = None,
) -> pd.DataFrame:
    """LLM visibility scores, optionally filtered by platform, week, and DMA.

    Args:
        platform: One of the six LLM platforms (e.g. 'chatgpt', 'perplexity').
                  None returns all platforms.
        period:   ISO week start date string (e.g. '2025-05-05'). None = all periods.
        market:   DMA name (e.g. 'Cincinnati'). None = all markets.

    Returns:
        DataFrame with columns:
            week_start, platform, prompt_text, prompt_category, market_dma,
            brand, mentioned, position, mention_rate, sentiment_score, citation_rate
    """
    if platform is not None and platform not in _VALID_PLATFORMS_LLM:
        raise ValueError(
            f"platform must be one of {sorted(_VALID_PLATFORMS_LLM)}, got {platform!r}"
        )

    clauses: list[str] = []
    params: list = []
    if platform is not None:
        clauses.append("platform = ?")
        params.append(platform)
    if period is not None:
        clauses.append("week_start = ?")
        params.append(period)
    if market is not None:
        clauses.append("market_dma = ?")
        params.append(market)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    conn = get_connection()
    try:
        rows = conn.execute(
            f"""
            SELECT
                week_start, platform, prompt_text, prompt_category, market_dma,
                brand, mentioned, position, mention_rate, sentiment_score, citation_rate
            FROM llm_visibility
            {where}
            ORDER BY week_start, platform, brand
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    cols = [
        "week_start", "platform", "prompt_text", "prompt_category", "market_dma",
        "brand", "mentioned", "position", "mention_rate", "sentiment_score", "citation_rate",
    ]
    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        return df

    df["mentioned"] = df["mentioned"].astype(bool)
    df["position"] = pd.to_numeric(df["position"], errors="coerce")
    for col in ("mention_rate", "sentiment_score", "citation_rate"):
        df[col] = df[col].astype(float)
    return df


# ---------------------------------------------------------------------------
# 2. load_competitive_aeo
# ---------------------------------------------------------------------------


def load_competitive_aeo(
    competitors: Optional[list[str]] = None,
    period: Optional[str] = None,
) -> pd.DataFrame:
    """AEO competitor comparison data from aeo_competitor_scores.

    Args:
        competitors: List of competitor names to include. None = all competitors.
        period:      ISO week_ending date string. None = all periods.

    Returns:
        DataFrame with columns:
            week_ending, competitor_name, platform, mention_rate, avg_position,
            share_of_voice, sentiment_score, citation_rate
    """
    clauses: list[str] = []
    params: list = []

    if competitors is not None and len(competitors) > 0:
        placeholders = ", ".join("?" for _ in competitors)
        clauses.append(f"competitor_name IN ({placeholders})")
        params.extend(competitors)
    if period is not None:
        clauses.append("week_ending = ?")
        params.append(period)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    conn = get_connection()
    try:
        rows = conn.execute(
            f"""
            SELECT
                week_ending, competitor_name, platform,
                mention_rate, avg_position, share_of_voice,
                sentiment_score, citation_rate
            FROM aeo_competitor_scores
            {where}
            ORDER BY week_ending, competitor_name, platform
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    cols = [
        "week_ending", "competitor_name", "platform",
        "mention_rate", "avg_position", "share_of_voice",
        "sentiment_score", "citation_rate",
    ]
    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        return df

    for col in ("mention_rate", "avg_position", "share_of_voice", "sentiment_score", "citation_rate"):
        df[col] = df[col].astype(float)
    return df


# ---------------------------------------------------------------------------
# 3. load_prompt_drilldown
# ---------------------------------------------------------------------------


def load_prompt_drilldown(
    platform: Optional[str] = None,
    prompt_category: Optional[str] = None,
    period: Optional[str] = None,
) -> pd.DataFrame:
    """Per-prompt AEO results from aeo_weekly_readings.

    Args:
        platform:        AEO platform name (e.g. 'ChatGPT'). None = all platforms.
        prompt_category: Not a direct column in aeo_weekly_readings; used for
                         prefix-based filtering on the prompt text (e.g. prompts
                         known to belong to a category). When None, returns all.
                         NOTE: aeo_weekly_readings has no category column, so this
                         loader applies a client-side filter when provided.
        period:          ISO week_ending string. None = all periods.

    Returns:
        DataFrame with columns:
            week_ending, platform, prompt, mention_rate, avg_position,
            share_of_voice, sentiment_score, citation_rate
    """
    clauses: list[str] = []
    params: list = []

    if platform is not None:
        clauses.append("platform = ?")
        params.append(platform)
    if period is not None:
        clauses.append("week_ending = ?")
        params.append(period)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    conn = get_connection()
    try:
        rows = conn.execute(
            f"""
            SELECT
                week_ending, platform, prompt,
                mention_rate, avg_position, share_of_voice,
                sentiment_score, citation_rate
            FROM aeo_weekly_readings
            {where}
            ORDER BY week_ending, platform, prompt
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    cols = [
        "week_ending", "platform", "prompt",
        "mention_rate", "avg_position", "share_of_voice",
        "sentiment_score", "citation_rate",
    ]
    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        return df

    for col in ("mention_rate", "avg_position", "share_of_voice", "sentiment_score", "citation_rate"):
        df[col] = df[col].astype(float)

    # Client-side category filter — aeo_weekly_readings has no category column
    if prompt_category is not None:
        # Map categories to prompt keyword prefixes used in the seed
        _CATEGORY_KEYWORDS: dict[str, list[str]] = {
            "checking":      ["checking", "bank account", "direct deposit", "overdraft"],
            "savings":       ["savings", "high yield", "CD rates", "money market", "APY"],
            "mortgage":      ["mortgage", "home equity", "HELOC", "refinance mortgage"],
            "credit_card":   ["credit card", "cash back", "travel rewards"],
            "auto_loan":     ["auto loan", "car loan"],
            "personal_loan": ["personal loan", "debt consolidation"],
        }
        kws = _CATEGORY_KEYWORDS.get(prompt_category, [])
        if kws:
            pattern = "|".join(kws)
            mask = df["prompt"].str.contains(pattern, case=False, na=False)
            df = df[mask].reset_index(drop=True)
        else:
            # Unknown category — no prompts can match; return empty
            df = df.iloc[0:0].reset_index(drop=True)

    return df


# ---------------------------------------------------------------------------
# 4. load_seo_rankings
# ---------------------------------------------------------------------------


def load_seo_rankings(
    category: Optional[str] = None,
    period: Optional[str] = None,
) -> pd.DataFrame:
    """SEO keyword rankings, optionally filtered by product category and week.

    Args:
        category: Product category (e.g. 'checking'). None = all categories.
        period:   ISO week_start date string. None = all periods.

    Returns:
        DataFrame with columns:
            week_start, keyword, product_category, rank_position,
            rank_page, search_volume, rank_change
    """
    if category is not None and category not in _VALID_CATEGORIES:
        raise ValueError(
            f"category must be one of {sorted(_VALID_CATEGORIES)}, got {category!r}"
        )

    clauses: list[str] = []
    params: list = []

    if category is not None:
        clauses.append("product_category = ?")
        params.append(category)
    if period is not None:
        clauses.append("week_start = ?")
        params.append(period)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    conn = get_connection()
    try:
        rows = conn.execute(
            f"""
            SELECT
                week_start, keyword, product_category,
                rank_position, rank_page, search_volume, rank_change
            FROM seo_rankings
            {where}
            ORDER BY week_start, rank_position
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    cols = [
        "week_start", "keyword", "product_category",
        "rank_position", "rank_page", "search_volume", "rank_change",
    ]
    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        return df

    df["rank_position"] = df["rank_position"].astype(int)
    df["rank_page"] = df["rank_page"].astype(int)
    df["search_volume"] = df["search_volume"].astype(int)
    df["rank_change"] = df["rank_change"].astype(int)
    return df


# ---------------------------------------------------------------------------
# 5. load_seo_traffic
# ---------------------------------------------------------------------------


def load_seo_traffic(period: Optional[str] = None) -> pd.DataFrame:
    """Organic traffic by category, optionally filtered by week.

    Args:
        period: ISO week_start date string. None = all periods.

    Returns:
        DataFrame with columns:
            week_start, product_category, organic_sessions,
            organic_accounts, bounce_rate
    """
    where = "WHERE week_start = ?" if period else ""
    params: list = [period] if period else []

    conn = get_connection()
    try:
        rows = conn.execute(
            f"""
            SELECT
                week_start, product_category,
                organic_sessions, organic_accounts, bounce_rate
            FROM seo_traffic
            {where}
            ORDER BY week_start, product_category
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    cols = [
        "week_start", "product_category",
        "organic_sessions", "organic_accounts", "bounce_rate",
    ]
    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        return df

    df["organic_sessions"] = df["organic_sessions"].astype(int)
    df["organic_accounts"] = df["organic_accounts"].astype(int)
    df["bounce_rate"] = df["bounce_rate"].astype(float)
    return df


# ---------------------------------------------------------------------------
# 6. load_rank_change_alerts
# ---------------------------------------------------------------------------


def load_rank_change_alerts(threshold: int = 5) -> pd.DataFrame:
    """Keywords with |rank_change| >= threshold (significant movers).

    Args:
        threshold: Absolute rank change magnitude to flag (default 5).
                   Must be >= 1.

    Returns:
        DataFrame with columns:
            week_start, keyword, product_category, rank_position,
            rank_change, search_volume, direction
        sorted by abs(rank_change) descending.

        direction: 'improved' (rank_change < 0) or 'dropped' (rank_change > 0)
    """
    if threshold < 1:
        raise ValueError(f"threshold must be >= 1, got {threshold}")

    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                week_start, keyword, product_category,
                rank_position, rank_change, search_volume
            FROM seo_rankings
            WHERE ABS(rank_change) >= ?
            ORDER BY ABS(rank_change) DESC, week_start DESC
            """,
            [threshold],
        ).fetchall()
    finally:
        conn.close()

    cols = [
        "week_start", "keyword", "product_category",
        "rank_position", "rank_change", "search_volume",
    ]
    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        df["direction"] = pd.Series(dtype=str)
        return df

    df["rank_position"] = df["rank_position"].astype(int)
    df["rank_change"] = df["rank_change"].astype(int)
    df["search_volume"] = df["search_volume"].astype(int)
    df["direction"] = df["rank_change"].apply(
        lambda x: "improved" if x < 0 else "dropped"
    )
    return df


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------


def compute_mention_rate(df: pd.DataFrame) -> float:
    """Average mention_rate across all rows in df.

    Args:
        df: DataFrame with a 'mention_rate' column (float, range 0–1).

    Returns:
        Mean mention rate as float. Returns 0.0 for empty DataFrames.
    """
    if df.empty or "mention_rate" not in df.columns:
        return 0.0
    return float(df["mention_rate"].mean())


def compute_avg_position(df: pd.DataFrame) -> float:
    """Average position across all non-null position values in df.

    Works with both llm_visibility (column: 'position') and
    aeo_weekly_readings (column: 'avg_position').

    Args:
        df: DataFrame with a 'position' or 'avg_position' column.

    Returns:
        Mean position as float. Returns 0.0 for empty DataFrames.
    """
    if df.empty:
        return 0.0
    if "avg_position" in df.columns:
        series = pd.to_numeric(df["avg_position"], errors="coerce").dropna()
    elif "position" in df.columns:
        series = pd.to_numeric(df["position"], errors="coerce").dropna()
    else:
        return 0.0
    return float(series.mean()) if not series.empty else 0.0


def compute_share_of_voice(df: pd.DataFrame, brand: str) -> float:
    """Brand's share of voice relative to all brands in df.

    Share of voice = brand's total mention_rate / sum of all mention_rates.

    Args:
        df:    DataFrame with 'brand' and 'mention_rate' columns.
        brand: The brand name to compute SoV for.

    Returns:
        Share of voice as float in [0, 1]. Returns 0.0 when df is empty
        or brand is not present.
    """
    if df.empty or "brand" not in df.columns or "mention_rate" not in df.columns:
        return 0.0
    total = float(df["mention_rate"].sum())
    if total == 0:
        return 0.0
    brand_total = float(df.loc[df["brand"] == brand, "mention_rate"].sum())
    return brand_total / total


def compute_citation_rate(df: pd.DataFrame) -> float:
    """Average citation_rate across all rows in df.

    Args:
        df: DataFrame with a 'citation_rate' column (float, range 0–1).

    Returns:
        Mean citation rate as float. Returns 0.0 for empty DataFrames.
    """
    if df.empty or "citation_rate" not in df.columns:
        return 0.0
    return float(df["citation_rate"].mean())
