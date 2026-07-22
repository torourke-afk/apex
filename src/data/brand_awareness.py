"""
Brand Awareness Tracker — MSV-based competitive intelligence
=============================================================

Tracks a brand's Monthly Search Volume (MSV) relative to a configurable
peer set. Supports national-level data via SEMrush API and DMA-level
data via Google Ads Keyword Planner API (stubbed for future integration).

Key concepts:
    - **MSV**: Monthly Search Volume for a branded keyword (e.g., "fifth third bank")
    - **Share of Search**: brand_msv / sum(all_peer_msv) — proxy for brand awareness
    - **Peer Set**: configurable group of competitor brands to benchmark against
    - **Geo Scope**: National (SEMrush) or DMA-level (Google Ads, future)

Data flow:
    1. User enters their brand domain/name
    2. System recommends competitors (SEMrush organic competitors + presets)
    3. User confirms/edits peer set
    4. System pulls MSV for all brands at configured cadence
    5. Dashboard shows time-series, share-of-search, and peer comparison

Author: generated for Tyler / RVGT
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SEMRUSH_API_KEY = os.environ.get("SEMRUSH_API_KEY", "")
GOOGLE_ADS_DEVELOPER_TOKEN = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", "")

GeoScope = Literal["national", "dma"]
TrackingInterval = Literal["daily", "weekly", "monthly", "quarterly"]


# ---------------------------------------------------------------------------
# FITB Preset — known competitor set for Fifth Third Bank
# ---------------------------------------------------------------------------

FITB_PRESET = {
    "brand": "Fifth Third Bank",
    "brand_keyword": "fifth third bank",
    "domain": "53.com",
    "competitors": [
        {"name": "Huntington Bank", "keyword": "huntington bank", "domain": "huntington.com"},
        {"name": "KeyBank", "keyword": "keybank", "domain": "key.com"},
        {"name": "PNC Bank", "keyword": "pnc bank", "domain": "pnc.com"},
        {"name": "U.S. Bank", "keyword": "us bank", "domain": "usbank.com"},
        {"name": "Truist", "keyword": "truist bank", "domain": "truist.com"},
        {"name": "Citizens Bank", "keyword": "citizens bank", "domain": "citizensbank.com"},
        {"name": "Regions Bank", "keyword": "regions bank", "domain": "regions.com"},
        {"name": "M&T Bank", "keyword": "m&t bank", "domain": "mtb.com"},
    ],
}

# Additional presets for common bank peer groups
PEER_PRESETS: dict[str, list[dict[str, str]]] = {
    "Super Regional Banks": [
        {"name": "PNC Bank", "keyword": "pnc bank", "domain": "pnc.com"},
        {"name": "U.S. Bank", "keyword": "us bank", "domain": "usbank.com"},
        {"name": "Truist", "keyword": "truist bank", "domain": "truist.com"},
        {"name": "Citizens Bank", "keyword": "citizens bank", "domain": "citizensbank.com"},
        {"name": "M&T Bank", "keyword": "m&t bank", "domain": "mtb.com"},
        {"name": "Regions Bank", "keyword": "regions bank", "domain": "regions.com"},
        {"name": "KeyBank", "keyword": "keybank", "domain": "key.com"},
        {"name": "Huntington Bank", "keyword": "huntington bank", "domain": "huntington.com"},
    ],
    "Ohio/Midwest Footprint": [
        {"name": "Huntington Bank", "keyword": "huntington bank", "domain": "huntington.com"},
        {"name": "KeyBank", "keyword": "keybank", "domain": "key.com"},
        {"name": "PNC Bank", "keyword": "pnc bank", "domain": "pnc.com"},
        {"name": "U.S. Bank", "keyword": "us bank", "domain": "usbank.com"},
        {"name": "Comerica", "keyword": "comerica bank", "domain": "comerica.com"},
    ],
    "Southeast Footprint": [
        {"name": "Truist", "keyword": "truist bank", "domain": "truist.com"},
        {"name": "Regions Bank", "keyword": "regions bank", "domain": "regions.com"},
        {"name": "Synovus", "keyword": "synovus bank", "domain": "synovus.com"},
        {"name": "Atlantic Capital", "keyword": "atlantic capital bank", "domain": "atlanticcapital.com"},
    ],
    "National Digital": [
        {"name": "Chase", "keyword": "chase bank", "domain": "chase.com"},
        {"name": "Bank of America", "keyword": "bank of america", "domain": "bankofamerica.com"},
        {"name": "Wells Fargo", "keyword": "wells fargo", "domain": "wellsfargo.com"},
        {"name": "Capital One", "keyword": "capital one bank", "domain": "capitalone.com"},
        {"name": "Ally Bank", "keyword": "ally bank", "domain": "ally.com"},
    ],
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class BrandMSV:
    """Single MSV observation for a brand at a point in time."""
    brand: str
    keyword: str
    msv: int                     # monthly search volume
    date: _dt.date               # observation month (1st of month)
    geo: str                     # "US" for national, DMA code for local
    trend: list[int] | None = None  # 12-month trend array (0-100 relative)


@dataclass
class PeerComparison:
    """Computed peer comparison snapshot."""
    date: _dt.date
    geo: str
    brand_msv: int
    total_peer_msv: int          # sum of all peers (including brand)
    share_of_search: float       # brand_msv / total_peer_msv
    peer_data: list[dict]        # [{brand, keyword, msv, share}]
    rank: int                    # brand's rank in peer set by MSV


@dataclass
class TrackerConfig:
    """Full tracker configuration for persistence."""
    brand_name: str
    brand_keyword: str
    brand_domain: str
    competitors: list[dict[str, str]]   # [{name, keyword, domain}]
    geo_scope: GeoScope = "national"
    dma_codes: list[str] = field(default_factory=list)
    interval: TrackingInterval = "monthly"
    created: _dt.date = field(default_factory=_dt.date.today)

    def all_keywords(self) -> list[str]:
        """All keywords to track (brand + competitors)."""
        return [self.brand_keyword] + [c["keyword"] for c in self.competitors]

    def all_brands(self) -> list[dict[str, str]]:
        """All brands as dicts (brand + competitors)."""
        return [
            {"name": self.brand_name, "keyword": self.brand_keyword, "domain": self.brand_domain},
        ] + self.competitors


# ---------------------------------------------------------------------------
# SEMrush API client (real + mock)
# ---------------------------------------------------------------------------

def _semrush_keyword_metrics(keyword: str, country: str = "us",
                              month: str | None = None) -> dict | None:
    """Call SEMrush Keyword Metrics API v4.

    Returns dict with keys: search_volume, cpc, trend (list[int]), or None on error.
    Requires SEMRUSH_API_KEY environment variable.

    Endpoint: GET https://api.semrush.com/apis/v4/keywords/v1/metrics
    Auth: Authorization: Apikey {key}
    Cost: 20 API units per request
    """
    if not SEMRUSH_API_KEY:
        return None

    try:
        import requests
        params = {"keyword": keyword, "country": country}
        if month:
            params["month"] = month

        resp = requests.get(
            "https://api.semrush.com/apis/v4/keywords/v1/metrics",
            params=params,
            headers={"Authorization": f"Apikey {SEMRUSH_API_KEY}"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "search_volume": data.get("search_volume", 0),
            "cpc": data.get("cpc", 0.0),
            "trend": data.get("trends", []),
        }
    except Exception:
        return None


def _semrush_organic_competitors(domain: str, country: str = "us",
                                  limit: int = 10) -> list[dict] | None:
    """Get organic competitors for a domain via SEMrush.

    Endpoint: GET https://api.semrush.com/?type=domain_organic_organic
    Cost: 40 API units per line
    """
    if not SEMRUSH_API_KEY:
        return None

    try:
        import requests
        resp = requests.get(
            "https://api.semrush.com/",
            params={
                "type": "domain_organic_organic",
                "key": SEMRUSH_API_KEY,
                "domain": domain,
                "database": country,
                "display_limit": str(limit),
                "export_columns": "Dn,Cr,Np,Or,Ot,Oc,Ad",
            },
            timeout=15,
        )
        resp.raise_for_status()
        lines = resp.text.strip().split("\n")
        if len(lines) < 2:
            return []
        headers = lines[0].split(";")
        results = []
        for line in lines[1:]:
            vals = line.split(";")
            if len(vals) >= 2:
                results.append({
                    "domain": vals[0],
                    "common_keywords": int(vals[1]) if vals[1].isdigit() else 0,
                })
        return results
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Synthetic data generator (for development without API keys)
# ---------------------------------------------------------------------------

def _generate_synthetic_msv(config: TrackerConfig,
                             months: int = 24,
                             seed: int = 42) -> pd.DataFrame:
    """Generate realistic synthetic MSV time-series for all brands in the config.

    Produces monthly observations from (today - months) to today, with:
    - Realistic absolute MSV ranges for bank brands
    - Seasonal patterns (Q1 dip, Q4 lift)
    - Correlated but independent noise per brand
    - Trend components reflecting market position

    Returns DataFrame with columns:
        brand, keyword, date, geo, msv, trend_index
    """
    rng = np.random.default_rng(seed)
    today = _dt.date.today().replace(day=1)
    dates = [
        (today - _dt.timedelta(days=30 * i)).replace(day=1)
        for i in range(months - 1, -1, -1)
    ]

    # Base MSV by brand size tier (realistic bank search volumes)
    _MSV_TIERS = {
        # Mega banks: 500K-2M monthly
        "chase bank": (1_200_000, 0.02),
        "bank of america": (900_000, 0.01),
        "wells fargo": (800_000, 0.01),
        "capital one bank": (600_000, 0.03),
        # Super regionals: 100K-500K
        "pnc bank": (350_000, 0.02),
        "us bank": (300_000, 0.01),
        "truist bank": (250_000, 0.04),  # newer brand, growing
        "citizens bank": (180_000, 0.01),
        "m&t bank": (150_000, 0.02),
        "regions bank": (140_000, 0.01),
        "keybank": (130_000, 0.02),
        "huntington bank": (120_000, 0.03),
        "fifth third bank": (165_000, 0.02),
        # Smaller regionals: 20K-100K
        "comerica bank": (65_000, 0.01),
        "synovus bank": (28_000, 0.02),
        "atlantic capital bank": (8_000, 0.01),
        "ally bank": (450_000, 0.04),  # digital-first, growing
    }

    rows = []
    for brand_info in config.all_brands():
        kw = brand_info["keyword"]
        name = brand_info["name"]

        # Look up base MSV or estimate from keyword
        base_msv, trend_rate = _MSV_TIERS.get(kw, (50_000, 0.02))

        for i, dt in enumerate(dates):
            # Seasonal: Q1 dip (-5%), Q4 lift (+8%), summer neutral
            month = dt.month
            seasonal = {
                1: -0.05, 2: -0.03, 3: -0.01,
                4: 0.01, 5: 0.02, 6: 0.0,
                7: -0.01, 8: 0.01, 9: 0.03,
                10: 0.05, 11: 0.06, 12: 0.08,
            }.get(month, 0.0)

            # Trend: gentle growth/decline over time
            trend_factor = 1.0 + trend_rate * (i / months - 0.5)

            # Noise: ±8% monthly variance
            noise = 1.0 + rng.normal(0, 0.08)

            msv = int(base_msv * trend_factor * (1 + seasonal) * noise)
            msv = max(100, msv)  # floor

            # Trend index (0-100 scale, relative to max in this series)
            rows.append({
                "brand": name,
                "keyword": kw,
                "date": dt,
                "geo": "US",
                "msv": msv,
            })

    df = pd.DataFrame(rows)

    # Compute trend_index per brand (0-100 relative to brand's own max)
    df["trend_index"] = (
        df.groupby("brand")["msv"]
        .transform(lambda s: ((s / s.max()) * 100).astype(int).clip(0, 100))
    )
    return df.sort_values(["date", "brand"]).reset_index(drop=True)


def _generate_synthetic_dma_msv(config: TrackerConfig,
                                 dma_codes: list[str] | None = None,
                                 months: int = 12,
                                 seed: int = 43) -> pd.DataFrame:
    """Generate DMA-level synthetic MSV data.

    DMA volumes are proportional to national but scaled by DMA population weight.
    Uses the FITB footprint DMAs by default.
    """
    rng = np.random.default_rng(seed)

    # FITB footprint DMAs with approximate population shares of national search
    _DMA_WEIGHTS = {
        "515": ("Cincinnati", 0.018),
        "535": ("Columbus", 0.016),
        "510": ("Cleveland", 0.015),
        "539": ("Tampa", 0.022),
        "528": ("Miami", 0.028),
        "524": ("Atlanta", 0.032),
        "659": ("Nashville", 0.014),
        "517": ("Charlotte", 0.016),
        "602": ("Chicago", 0.040),
        "505": ("Detroit", 0.020),
        "623": ("Dallas", 0.035),
        "618": ("Houston", 0.030),
    }

    if dma_codes:
        dma_map = {k: v for k, v in _DMA_WEIGHTS.items() if k in dma_codes}
    else:
        dma_map = _DMA_WEIGHTS

    # Get national data first as base
    national_df = _generate_synthetic_msv(config, months=months, seed=seed)

    rows = []
    for dma_code, (dma_name, weight) in dma_map.items():
        for _, nat_row in national_df.iterrows():
            # DMA MSV = national * weight * local_noise
            local_noise = 1.0 + rng.normal(0, 0.15)  # more variance at DMA level
            msv = max(10, int(nat_row["msv"] * weight * local_noise))
            rows.append({
                "brand": nat_row["brand"],
                "keyword": nat_row["keyword"],
                "date": nat_row["date"],
                "geo": f"DMA-{dma_code}",
                "dma_name": dma_name,
                "msv": msv,
            })

    df = pd.DataFrame(rows)

    df["trend_index"] = (
        df.groupby(["brand", "geo"])["msv"]
        .transform(lambda s: ((s / s.max()) * 100).astype(int).clip(0, 100) if s.max() > 0 else 0)
    )
    return df.sort_values(["date", "geo", "brand"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Competitor recommendation engine
# ---------------------------------------------------------------------------

def recommend_competitors(brand_domain: str,
                           brand_name: str = "",
                           limit: int = 8) -> list[dict[str, str]]:
    """Recommend competitors for a brand.

    Strategy:
    1. Try SEMrush organic competitors API
    2. Fall back to preset peer groups based on brand name matching
    3. Return a mix of both if SEMrush works

    Returns list of dicts: [{name, keyword, domain}]
    """
    # Try SEMrush API first
    api_competitors = _semrush_organic_competitors(brand_domain, limit=limit)
    if api_competitors:
        results = []
        for comp in api_competitors[:limit]:
            domain = comp["domain"]
            # Clean domain name to brand name
            name = domain.replace(".com", "").replace(".org", "").replace("www.", "")
            name = name.replace("-", " ").title()
            results.append({
                "name": name,
                "keyword": f"{name.lower()} bank" if "bank" not in name.lower() else name.lower(),
                "domain": domain,
            })
        return results

    # Fallback: match against presets
    brand_lower = brand_name.lower()

    # Check if this is FITB
    if any(kw in brand_lower for kw in ["fifth third", "53", "5/3", "fitb"]):
        return FITB_PRESET["competitors"][:limit]

    # Check preset peer groups for overlap
    for group_name, peers in PEER_PRESETS.items():
        for peer in peers:
            if peer["domain"] == brand_domain or peer["name"].lower() in brand_lower:
                # Found a match — return that preset minus the brand itself
                return [p for p in peers if p["domain"] != brand_domain][:limit]

    # Generic fallback: Super Regional Banks preset
    return PEER_PRESETS["Super Regional Banks"][:limit]


# ---------------------------------------------------------------------------
# Share of Search computation
# ---------------------------------------------------------------------------

def compute_share_of_search(msv_df: pd.DataFrame,
                             brand_keyword: str) -> pd.DataFrame:
    """Compute Share of Search for each date × geo.

    Share of Search = brand_msv / sum(all_brand_msv_in_peer_set)

    This is a well-established proxy for brand awareness and market share
    (Les Binet, IPA research).

    Returns DataFrame with columns:
        date, geo, brand_msv, total_msv, share_of_search, rank
    """
    results = []
    for (date, geo), grp in msv_df.groupby(["date", "geo"]):
        total = grp["msv"].sum()
        brand_row = grp[grp["keyword"] == brand_keyword]
        brand_msv = int(brand_row["msv"].iloc[0]) if not brand_row.empty else 0
        share = brand_msv / total if total > 0 else 0.0

        # Rank (1 = highest MSV)
        grp_sorted = grp.sort_values("msv", ascending=False).reset_index(drop=True)
        rank_idx = grp_sorted[grp_sorted["keyword"] == brand_keyword].index
        rank = int(rank_idx[0]) + 1 if len(rank_idx) > 0 else 0

        results.append({
            "date": date,
            "geo": geo,
            "brand_msv": brand_msv,
            "total_msv": int(total),
            "share_of_search": round(share, 4),
            "rank": rank,
        })

    return pd.DataFrame(results).sort_values("date").reset_index(drop=True)


def compute_peer_comparison(msv_df: pd.DataFrame,
                             date: _dt.date | None = None,
                             geo: str = "US") -> pd.DataFrame:
    """Compute peer comparison table for a specific date and geo.

    Returns DataFrame with columns:
        brand, keyword, msv, share, rank, msv_delta, share_delta
    (deltas are vs prior month)
    """
    if date is None:
        date = msv_df["date"].max()

    # Current period
    current = msv_df[(msv_df["date"] == date) & (msv_df["geo"] == geo)].copy()
    if current.empty:
        # Find closest date
        all_dates = msv_df[msv_df["geo"] == geo]["date"].unique()
        if len(all_dates) == 0:
            return pd.DataFrame()
        date = max(all_dates)
        current = msv_df[(msv_df["date"] == date) & (msv_df["geo"] == geo)].copy()

    total = current["msv"].sum()
    current["share"] = (current["msv"] / total * 100).round(1) if total > 0 else 0.0
    current = current.sort_values("msv", ascending=False).reset_index(drop=True)
    current["rank"] = range(1, len(current) + 1)

    # Prior period for deltas
    prior_date = (pd.Timestamp(date) - pd.DateOffset(months=1)).date()
    prior_date = prior_date.replace(day=1)
    prior = msv_df[(msv_df["date"] == prior_date) & (msv_df["geo"] == geo)]

    if not prior.empty:
        prior_total = prior["msv"].sum()
        prior_share = {}
        prior_msv = {}
        for _, row in prior.iterrows():
            kw = row["keyword"]
            prior_msv[kw] = row["msv"]
            prior_share[kw] = (row["msv"] / prior_total * 100) if prior_total > 0 else 0.0

        current["msv_delta"] = current["keyword"].map(
            lambda kw: current.loc[current["keyword"] == kw, "msv"].iloc[0] - prior_msv.get(kw, 0)
        )
        current["share_delta"] = current["keyword"].map(
            lambda kw: current.loc[current["keyword"] == kw, "share"].iloc[0] - prior_share.get(kw, 0.0)
        )
    else:
        current["msv_delta"] = 0
        current["share_delta"] = 0.0

    return current[["brand", "keyword", "msv", "share", "rank", "msv_delta", "share_delta"]]


# ---------------------------------------------------------------------------
# Cached loaders for Streamlit pages
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner="Loading brand awareness data…")
def load_msv_data(config_json: str) -> pd.DataFrame:
    """Load MSV time-series data for a tracker configuration.

    Tries SEMrush API first, falls back to synthetic data.
    Config is passed as JSON string for Streamlit cache compatibility.
    """
    config = _config_from_json(config_json)

    if SEMRUSH_API_KEY:
        # Try live API
        rows = []
        for brand_info in config.all_brands():
            data = _semrush_keyword_metrics(brand_info["keyword"])
            if data:
                rows.append({
                    "brand": brand_info["name"],
                    "keyword": brand_info["keyword"],
                    "date": _dt.date.today().replace(day=1),
                    "geo": "US",
                    "msv": data["search_volume"],
                    "trend_index": 0,
                })
        if rows:
            return pd.DataFrame(rows)

    # Fallback: synthetic data
    return _generate_synthetic_msv(config)


@st.cache_data(ttl=3600, show_spinner="Loading DMA-level brand data…")
def load_dma_msv_data(config_json: str,
                       dma_codes_json: str = "[]") -> pd.DataFrame:
    """Load DMA-level MSV data. Always synthetic for now (Google Ads API TBD)."""
    config = _config_from_json(config_json)
    dma_codes = json.loads(dma_codes_json) if dma_codes_json else []
    return _generate_synthetic_dma_msv(config, dma_codes=dma_codes or None)


@st.cache_data(ttl=3600)
def load_share_of_search(config_json: str, geo: str = "US") -> pd.DataFrame:
    """Compute Share of Search time-series."""
    config = _config_from_json(config_json)
    msv_df = load_msv_data(config_json)
    if geo != "US":
        dma_df = load_dma_msv_data(config_json)
        msv_df = dma_df[dma_df["geo"] == geo] if not dma_df.empty else msv_df
    return compute_share_of_search(msv_df, config.brand_keyword)


def get_available_dmas() -> list[dict[str, str]]:
    """Return list of available DMAs from the markets table or fallback."""
    try:
        from src.data.load_markets import load_markets
        markets = load_markets()
        return [
            {"dma": row["dma"], "state": row["state"]}
            for _, row in markets.iterrows()
        ]
    except Exception:
        # Fallback
        return [
            {"dma": "Cincinnati", "state": "OH"},
            {"dma": "Columbus", "state": "OH"},
            {"dma": "Cleveland", "state": "OH"},
            {"dma": "Chicago", "state": "IL"},
            {"dma": "Detroit", "state": "MI"},
            {"dma": "Atlanta", "state": "GA"},
            {"dma": "Tampa", "state": "FL"},
            {"dma": "Charlotte", "state": "NC"},
            {"dma": "Nashville", "state": "TN"},
            {"dma": "Dallas", "state": "TX"},
        ]


def get_latest_share_of_search(config_json: str) -> dict:
    """Get the most recent Share of Search metrics for scorecard KPI.

    Returns dict with: share, rank, peer_count, delta_share, brand_msv
    """
    try:
        sos_df = load_share_of_search(config_json)
        if sos_df.empty:
            return {"share": 0, "rank": 0, "peer_count": 0, "delta_share": 0, "brand_msv": 0}

        latest = sos_df.iloc[-1]
        prior = sos_df.iloc[-2] if len(sos_df) > 1 else latest

        config = _config_from_json(config_json)
        peer_count = len(config.competitors) + 1

        return {
            "share": float(latest["share_of_search"]),
            "rank": int(latest["rank"]),
            "peer_count": peer_count,
            "delta_share": float(latest["share_of_search"] - prior["share_of_search"]),
            "brand_msv": int(latest["brand_msv"]),
        }
    except Exception:
        return {"share": 0, "rank": 0, "peer_count": 0, "delta_share": 0, "brand_msv": 0}


# ---------------------------------------------------------------------------
# Config serialization (for Streamlit cache keys)
# ---------------------------------------------------------------------------

def config_to_json(config: TrackerConfig) -> str:
    """Serialize a TrackerConfig to JSON for use as a cache key."""
    return json.dumps({
        "brand_name": config.brand_name,
        "brand_keyword": config.brand_keyword,
        "brand_domain": config.brand_domain,
        "competitors": config.competitors,
        "geo_scope": config.geo_scope,
        "dma_codes": config.dma_codes,
        "interval": config.interval,
    }, sort_keys=True)


def _config_from_json(config_json: str) -> TrackerConfig:
    """Deserialize a TrackerConfig from JSON."""
    d = json.loads(config_json)
    return TrackerConfig(
        brand_name=d["brand_name"],
        brand_keyword=d["brand_keyword"],
        brand_domain=d["brand_domain"],
        competitors=d["competitors"],
        geo_scope=d.get("geo_scope", "national"),
        dma_codes=d.get("dma_codes", []),
        interval=d.get("interval", "monthly"),
    )


def default_fitb_config() -> TrackerConfig:
    """Return the default FITB tracker configuration."""
    return TrackerConfig(
        brand_name=FITB_PRESET["brand"],
        brand_keyword=FITB_PRESET["brand_keyword"],
        brand_domain=FITB_PRESET["domain"],
        competitors=FITB_PRESET["competitors"],
        geo_scope="national",
        interval="monthly",
    )
