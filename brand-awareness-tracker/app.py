"""
Brand Awareness Tracker — Standalone App
=========================================
MSV-based competitive brand intelligence. Tracks branded search volume
relative to a configurable peer set at national and DMA/footprint level.

Design system: Apex "Signal Deck" — calm, instrument-grade marketing console.
Dark glassmorphism, teal accent, Space Grotesk + JetBrains Mono.

Run:  streamlit run app.py
"""

from __future__ import annotations

import datetime as _dt
import json
import os
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1 — SIGNAL DECK DESIGN SYSTEM (ported from Apex)
# ═══════════════════════════════════════════════════════════════════════════

# Color tokens — dark glassmorphism
C = {
    "bg":             "#06080C",
    "bg_base":        "#0A0E14",
    "surface":        "#0D1118",
    "raised":         "#151B26",
    "input":          "#10151E",
    "text":           "#E8ECF4",
    "text2":          "#969FB2",
    "text3":          "#586173",
    "accent":         "#34E1D4",
    "accent_dark":    "#0C998D",
    "positive":       "#4FD89B",
    "warning":        "#F2B14C",
    "critical":       "#FF5C72",
    "border":         "rgba(255,255,255,0.07)",
    "border_solid":   "#1A2352",
    "glass_bg":       "rgba(13,17,24,0.75)",
    "glass_border":   "rgba(255,255,255,0.07)",
}

CHART_PALETTE = [
    "#34E1D4",   # teal accent
    "#7C8BFF",   # periwinkle
    "#4FD89B",   # green
    "#F2B14C",   # amber
    "#FF5C72",   # red
    "#0C998D",   # deep teal
    "#1D4ED8",   # blue
    "#969FB2",   # neutral
]

FONT_SANS = "'Space Grotesk', ui-sans-serif, system-ui, sans-serif"
FONT_MONO = "'JetBrains Mono', ui-monospace, 'SF Mono', monospace"


def _inject_signal_deck_css():
    """Inject the full Signal Deck design system via st.markdown."""
    st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

  :root {{
    --bg: {C["bg"]}; --surface: {C["surface"]}; --raised: {C["raised"]};
    --text: {C["text"]}; --text2: {C["text2"]}; --text3: {C["text3"]};
    --accent: {C["accent"]}; --positive: {C["positive"]};
    --warning: {C["warning"]}; --critical: {C["critical"]};
    --border: {C["border"]}; --glass-bg: {C["glass_bg"]};
    --font: {FONT_SANS}; --mono: {FONT_MONO};
  }}

  html, body, [class*="css"] {{
    font-family: {FONT_SANS} !important;
    color: {C["text"]};
    background-color: {C["bg"]} !important;
  }}
  .stApp {{
    background: radial-gradient(120% 90% at 78% -10%, {C["bg_base"]}, {C["bg"]} 60%) !important;
  }}
  .block-container {{ max-width: 1400px; padding: 1.5rem 2rem; }}

  h1, h2, h3, h4, h5, h6 {{
    font-family: {FONT_SANS} !important;
    color: {C["text"]} !important;
    font-weight: 700;
  }}
  p, span, div, label {{ font-family: {FONT_SANS} !important; }}

  /* Sidebar */
  section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {C["raised"]} 0%, {C["bg"]} 100%) !important;
    border-right: 1px solid {C["glass_border"]} !important;
  }}
  section[data-testid="stSidebar"] > div {{ background: transparent !important; }}

  /* Inputs */
  .stTextInput input, .stSelectbox select, .stMultiSelect div[data-baseweb] {{
    background: {C["input"]} !important;
    border: 1px solid {C["border"]} !important;
    color: {C["text"]} !important;
    border-radius: 10px !important;
    font-family: {FONT_SANS} !important;
  }}
  .stTextInput input:focus, .stSelectbox select:focus {{
    border-color: {C["accent"]} !important;
    box-shadow: 0 0 0 2px rgba(52,225,212,0.15) !important;
  }}

  /* Buttons */
  .stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, {C["accent"]} 0%, {C["accent_dark"]} 100%) !important;
    color: #04100F !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-family: {FONT_SANS} !important;
    transition: transform 140ms cubic-bezier(.2,0,0,1), box-shadow 140ms !important;
  }}
  .stButton > button[kind="primary"]:hover {{
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(52,225,212,0.25) !important;
  }}
  .stButton > button:not([kind="primary"]) {{
    background: {C["surface"]} !important;
    color: {C["text"]} !important;
    border: 1px solid {C["border"]} !important;
    border-radius: 10px !important;
    font-family: {FONT_SANS} !important;
  }}

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {{
    gap: 0.5rem;
    background: transparent !important;
    border-bottom: 1px solid {C["border"]} !important;
  }}
  .stTabs [data-baseweb="tab"] {{
    font-family: {FONT_SANS} !important;
    color: {C["text2"]} !important;
    border-radius: 8px 8px 0 0 !important;
    padding: 0.5rem 1rem !important;
    font-weight: 500 !important;
  }}
  .stTabs [aria-selected="true"] {{
    color: {C["accent"]} !important;
    border-bottom: 2px solid {C["accent"]} !important;
  }}

  /* Dataframes */
  .stDataFrame {{ border-radius: 10px; overflow: hidden; }}
  [data-testid="stDataFrame"] th {{
    background: {C["raised"]} !important;
    color: {C["text2"]} !important;
    font-family: {FONT_SANS} !important;
    font-size: 0.7rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
  }}

  /* Expander */
  .streamlit-expanderHeader {{
    font-family: {FONT_SANS} !important;
    color: {C["text2"]} !important;
    font-weight: 500 !important;
    background: {C["surface"]} !important;
    border-radius: 10px !important;
  }}

  /* Checkbox */
  .stCheckbox label span {{ color: {C["text"]} !important; font-family: {FONT_SANS} !important; }}

  /* Radio */
  .stRadio label {{ color: {C["text"]} !important; font-family: {FONT_SANS} !important; }}

  /* Multiselect pills */
  [data-baseweb="tag"] {{
    background: rgba(52,225,212,0.15) !important;
    border: 1px solid rgba(52,225,212,0.3) !important;
    color: {C["accent"]} !important;
    border-radius: 999px !important;
  }}
</style>""", unsafe_allow_html=True)


def card_start(title: str, subtitle: str = ""):
    """Begin a glassmorphic card container."""
    sub_html = f'<div style="font-size:0.7rem;color:{C["text3"]};margin-top:0.15rem;">{subtitle}</div>' if subtitle else ""
    st.markdown(f"""
<div style="background:{C["glass_bg"]};border:1px solid {C["glass_border"]};
border-radius:14px;padding:1.25rem 1.5rem;margin-bottom:1rem;
backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);">
<div style="margin-bottom:0.75rem;">
  <div style="font-size:0.85rem;font-weight:600;color:{C["text"]};letter-spacing:-0.01em;">{title}</div>
  {sub_html}
</div>""", unsafe_allow_html=True)


def card_end():
    """Close a glassmorphic card container."""
    st.markdown("</div>", unsafe_allow_html=True)


def kpi_card(title: str, value, fmt: str = "number",
             delta=None, delta_pct=None, subtitle: str = ""):
    """Render a single KPI card with Signal Deck styling."""
    # Format value
    if fmt == "percent":
        val_str = f"{value:.1f}%"
    elif fmt == "currency":
        val_str = f"${value:,.0f}" if value < 1_000_000 else f"${value/1_000_000:.1f}M"
    else:
        val_str = f"{value:,.0f}" if isinstance(value, (int, float)) else str(value)

    # Delta
    delta_html = ""
    if delta is not None:
        color = C["positive"] if delta >= 0 else C["critical"]
        arrow = "▲" if delta >= 0 else "▼"
        d_str = f"{abs(delta):.1f}" if isinstance(delta, float) else f"{abs(delta):,}"
        if fmt == "percent":
            d_str += "pp"
        pct_str = f" ({delta_pct:+.1f}%)" if delta_pct is not None else ""
        delta_html = f'<div style="font-size:0.7rem;color:{color};margin-top:0.2rem;">{arrow} {d_str}{pct_str}</div>'

    sub_html = f'<div style="font-size:0.6rem;color:{C["text3"]};margin-top:0.15rem;">{subtitle}</div>' if subtitle else ""

    st.markdown(f"""
<div style="background:{C["glass_bg"]};border:1px solid {C["glass_border"]};
border-radius:12px;padding:0.8rem 1rem;backdrop-filter:blur(8px);">
  <div style="font-size:0.6rem;font-weight:600;text-transform:uppercase;
  letter-spacing:0.06em;color:{C["text2"]};margin-bottom:0.25rem;">{title}</div>
  <div style="font-size:1.5rem;font-weight:700;color:{C["text"]};
  font-family:{FONT_MONO};font-variant-numeric:tabular-nums;
  letter-spacing:-0.02em;">{val_str}</div>
  {delta_html}{sub_html}
</div>""", unsafe_allow_html=True)


def plotly_layout(fig: go.Figure, height: int = 400, **kwargs):
    """Apply Signal Deck styling to a Plotly figure."""
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_SANS, color=C["text"], size=12),
        xaxis=dict(
            gridcolor=C["border"], linecolor=C["border"],
            tickfont=dict(color=C["text2"]),
        ),
        yaxis=dict(
            gridcolor=C["border"], linecolor=C["border"],
            tickfont=dict(color=C["text2"]),
        ),
        legend=dict(
            font=dict(color=C["text"], size=11),
            bgcolor="rgba(0,0,0,0)", borderwidth=0,
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
        ),
        margin=dict(l=60, r=20, t=30, b=40),
        hovermode="x unified",
        **kwargs,
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2 — DATA LAYER
# ═══════════════════════════════════════════════════════════════════════════

SEMRUSH_API_KEY = os.environ.get("SEMRUSH_API_KEY", "")
GeoScope = Literal["national", "dma"]
TrackingInterval = Literal["daily", "weekly", "monthly", "quarterly"]


# ── Presets ──────────────────────────────────────────────────────────────

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
    ],
    "National Digital": [
        {"name": "Chase", "keyword": "chase bank", "domain": "chase.com"},
        {"name": "Bank of America", "keyword": "bank of america", "domain": "bankofamerica.com"},
        {"name": "Wells Fargo", "keyword": "wells fargo", "domain": "wellsfargo.com"},
        {"name": "Capital One", "keyword": "capital one bank", "domain": "capitalone.com"},
        {"name": "Ally Bank", "keyword": "ally bank", "domain": "ally.com"},
    ],
}


# ── Config dataclass ─────────────────────────────────────────────────────

@dataclass
class TrackerConfig:
    brand_name: str
    brand_keyword: str
    brand_domain: str
    competitors: list[dict[str, str]]
    geo_scope: GeoScope = "national"
    dma_codes: list[str] = field(default_factory=list)
    interval: TrackingInterval = "monthly"

    def all_brands(self) -> list[dict[str, str]]:
        return [
            {"name": self.brand_name, "keyword": self.brand_keyword, "domain": self.brand_domain},
        ] + self.competitors


def config_to_json(config: TrackerConfig) -> str:
    return json.dumps({
        "brand_name": config.brand_name,
        "brand_keyword": config.brand_keyword,
        "brand_domain": config.brand_domain,
        "competitors": config.competitors,
        "geo_scope": config.geo_scope,
        "dma_codes": config.dma_codes,
        "interval": config.interval,
    }, sort_keys=True)


def _config_from_json(s: str) -> TrackerConfig:
    d = json.loads(s)
    return TrackerConfig(**d)


def default_fitb_config() -> TrackerConfig:
    return TrackerConfig(
        brand_name=FITB_PRESET["brand"],
        brand_keyword=FITB_PRESET["brand_keyword"],
        brand_domain=FITB_PRESET["domain"],
        competitors=FITB_PRESET["competitors"],
    )


# ── SEMrush API ──────────────────────────────────────────────────────────

def _semrush_keyword_metrics(keyword: str, country: str = "us") -> dict | None:
    """SEMrush Keyword Metrics v4. Returns {search_volume, cpc, trend} or None."""
    if not SEMRUSH_API_KEY:
        return None
    try:
        import requests
        resp = requests.get(
            "https://api.semrush.com/apis/v4/keywords/v1/metrics",
            params={"keyword": keyword, "country": country},
            headers={"Authorization": f"Apikey {SEMRUSH_API_KEY}"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return {"search_volume": data.get("search_volume", 0),
                "cpc": data.get("cpc", 0.0),
                "trend": data.get("trends", [])}
    except Exception:
        return None


def _semrush_organic_competitors(domain: str, country: str = "us",
                                  limit: int = 10) -> list[dict] | None:
    """Organic competitors via SEMrush v3."""
    if not SEMRUSH_API_KEY:
        return None
    try:
        import requests
        resp = requests.get(
            "https://api.semrush.com/",
            params={
                "type": "domain_organic_organic", "key": SEMRUSH_API_KEY,
                "domain": domain, "database": country,
                "display_limit": str(limit),
                "export_columns": "Dn,Cr,Np,Or,Ot,Oc,Ad",
            },
            timeout=15,
        )
        resp.raise_for_status()
        lines = resp.text.strip().split("\n")
        if len(lines) < 2:
            return []
        return [{"domain": line.split(";")[0],
                 "common_keywords": int(line.split(";")[1]) if line.split(";")[1].isdigit() else 0}
                for line in lines[1:] if ";" in line]
    except Exception:
        return None


# ── Competitor recommendations ───────────────────────────────────────────

def recommend_competitors(brand_domain: str, brand_name: str = "",
                           limit: int = 8) -> list[dict[str, str]]:
    """Recommend competitors. Tries SEMrush, falls back to presets."""
    api_comps = _semrush_organic_competitors(brand_domain, limit=limit)
    if api_comps:
        results = []
        for comp in api_comps[:limit]:
            d = comp["domain"]
            name = d.replace(".com", "").replace(".org", "").replace("www.", "")
            name = name.replace("-", " ").title()
            results.append({"name": name, "keyword": name.lower(), "domain": d})
        return results

    brand_lower = brand_name.lower()
    if any(kw in brand_lower for kw in ["fifth third", "53", "5/3", "fitb"]):
        return FITB_PRESET["competitors"][:limit]

    for _, peers in PEER_PRESETS.items():
        for peer in peers:
            if peer["domain"] == brand_domain or peer["name"].lower() in brand_lower:
                return [p for p in peers if p["domain"] != brand_domain][:limit]

    return PEER_PRESETS["Super Regional Banks"][:limit]


# ── Synthetic data ───────────────────────────────────────────────────────

_MSV_TIERS = {
    "chase bank": (1_200_000, 0.02), "bank of america": (900_000, 0.01),
    "wells fargo": (800_000, 0.01), "capital one bank": (600_000, 0.03),
    "pnc bank": (350_000, 0.02), "us bank": (300_000, 0.01),
    "truist bank": (250_000, 0.04), "citizens bank": (180_000, 0.01),
    "m&t bank": (150_000, 0.02), "regions bank": (140_000, 0.01),
    "keybank": (130_000, 0.02), "huntington bank": (120_000, 0.03),
    "fifth third bank": (165_000, 0.02), "comerica bank": (65_000, 0.01),
    "synovus bank": (28_000, 0.02), "ally bank": (450_000, 0.04),
}

_SEASONAL = {1: -0.05, 2: -0.03, 3: -0.01, 4: 0.01, 5: 0.02, 6: 0.0,
             7: -0.01, 8: 0.01, 9: 0.03, 10: 0.05, 11: 0.06, 12: 0.08}


def _generate_synthetic_msv(config: TrackerConfig, months: int = 24,
                             seed: int = 42) -> pd.DataFrame:
    """Generate realistic synthetic MSV time-series for all brands."""
    rng = np.random.default_rng(seed)
    today = _dt.date.today().replace(day=1)
    dates = [(today - _dt.timedelta(days=30 * i)).replace(day=1)
             for i in range(months - 1, -1, -1)]

    rows = []
    for brand_info in config.all_brands():
        kw, name = brand_info["keyword"], brand_info["name"]
        base_msv, trend_rate = _MSV_TIERS.get(kw, (50_000, 0.02))
        for i, dt in enumerate(dates):
            seasonal = _SEASONAL.get(dt.month, 0.0)
            trend_factor = 1.0 + trend_rate * (i / months - 0.5)
            noise = 1.0 + rng.normal(0, 0.08)
            msv = max(100, int(base_msv * trend_factor * (1 + seasonal) * noise))
            rows.append({"brand": name, "keyword": kw, "date": dt, "geo": "US", "msv": msv})

    df = pd.DataFrame(rows)
    df["trend_index"] = (
        df.groupby("brand")["msv"]
        .transform(lambda s: ((s / s.max()) * 100).astype(int).clip(0, 100))
    )
    return df.sort_values(["date", "brand"]).reset_index(drop=True)


_DMA_WEIGHTS = {
    "515": ("Cincinnati", 0.018), "535": ("Columbus", 0.016),
    "510": ("Cleveland", 0.015), "539": ("Tampa", 0.022),
    "528": ("Miami", 0.028), "524": ("Atlanta", 0.032),
    "659": ("Nashville", 0.014), "517": ("Charlotte", 0.016),
    "602": ("Chicago", 0.040), "505": ("Detroit", 0.020),
    "623": ("Dallas", 0.035), "618": ("Houston", 0.030),
}


def _generate_synthetic_dma_msv(config: TrackerConfig,
                                 dma_codes: list[str] | None = None,
                                 months: int = 12, seed: int = 43) -> pd.DataFrame:
    """Generate DMA-level synthetic MSV scaled from national."""
    rng = np.random.default_rng(seed)
    dma_map = {k: v for k, v in _DMA_WEIGHTS.items() if k in dma_codes} if dma_codes else _DMA_WEIGHTS
    national_df = _generate_synthetic_msv(config, months=months, seed=seed)

    rows = []
    for dma_code, (dma_name, weight) in dma_map.items():
        for _, nat_row in national_df.iterrows():
            local_noise = 1.0 + rng.normal(0, 0.15)
            msv = max(10, int(nat_row["msv"] * weight * local_noise))
            rows.append({
                "brand": nat_row["brand"], "keyword": nat_row["keyword"],
                "date": nat_row["date"], "geo": f"DMA-{dma_code}",
                "dma_name": dma_name, "msv": msv,
            })

    df = pd.DataFrame(rows)
    df["trend_index"] = (
        df.groupby(["brand", "geo"])["msv"]
        .transform(lambda s: ((s / s.max()) * 100).astype(int).clip(0, 100) if s.max() > 0 else 0)
    )
    return df.sort_values(["date", "geo", "brand"]).reset_index(drop=True)


# ── Computations ─────────────────────────────────────────────────────────

def compute_share_of_search(msv_df: pd.DataFrame, brand_keyword: str) -> pd.DataFrame:
    """Share of Search = brand_msv / total_msv per date × geo."""
    results = []
    for (date, geo), grp in msv_df.groupby(["date", "geo"]):
        total = grp["msv"].sum()
        brand_row = grp[grp["keyword"] == brand_keyword]
        brand_msv = int(brand_row["msv"].iloc[0]) if not brand_row.empty else 0
        share = brand_msv / total if total > 0 else 0.0
        grp_sorted = grp.sort_values("msv", ascending=False).reset_index(drop=True)
        rank_idx = grp_sorted[grp_sorted["keyword"] == brand_keyword].index
        rank = int(rank_idx[0]) + 1 if len(rank_idx) > 0 else 0
        results.append({"date": date, "geo": geo, "brand_msv": brand_msv,
                         "total_msv": int(total), "share_of_search": round(share, 4), "rank": rank})
    return pd.DataFrame(results).sort_values("date").reset_index(drop=True)


def compute_peer_comparison(msv_df: pd.DataFrame, date=None, geo="US") -> pd.DataFrame:
    """Peer comparison table for a given date/geo."""
    if date is None:
        date = msv_df["date"].max()
    current = msv_df[(msv_df["date"] == date) & (msv_df["geo"] == geo)].copy()
    if current.empty:
        all_dates = msv_df[msv_df["geo"] == geo]["date"].unique()
        if len(all_dates) == 0:
            return pd.DataFrame()
        date = max(all_dates)
        current = msv_df[(msv_df["date"] == date) & (msv_df["geo"] == geo)].copy()

    total = current["msv"].sum()
    current["share"] = (current["msv"] / total * 100).round(1) if total > 0 else 0.0
    current = current.sort_values("msv", ascending=False).reset_index(drop=True)
    current["rank"] = range(1, len(current) + 1)

    # Prior month deltas
    prior_date = (pd.Timestamp(date) - pd.DateOffset(months=1)).date().replace(day=1)
    prior = msv_df[(msv_df["date"] == prior_date) & (msv_df["geo"] == geo)]
    if not prior.empty:
        prior_total = prior["msv"].sum()
        prior_map = {row["keyword"]: (row["msv"], row["msv"] / prior_total * 100 if prior_total else 0)
                     for _, row in prior.iterrows()}
        current["msv_delta"] = current["keyword"].map(
            lambda kw: current.loc[current["keyword"] == kw, "msv"].iloc[0] - prior_map.get(kw, (0, 0))[0])
        current["share_delta"] = current["keyword"].map(
            lambda kw: current.loc[current["keyword"] == kw, "share"].iloc[0] - prior_map.get(kw, (0, 0))[1])
    else:
        current["msv_delta"] = 0
        current["share_delta"] = 0.0

    return current[["brand", "keyword", "msv", "share", "rank", "msv_delta", "share_delta"]]


# ── Cached loaders ───────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner="Loading brand awareness data…")
def load_msv_data(config_json: str) -> pd.DataFrame:
    config = _config_from_json(config_json)
    if SEMRUSH_API_KEY:
        rows = []
        for b in config.all_brands():
            data = _semrush_keyword_metrics(b["keyword"])
            if data:
                rows.append({"brand": b["name"], "keyword": b["keyword"],
                             "date": _dt.date.today().replace(day=1),
                             "geo": "US", "msv": data["search_volume"], "trend_index": 0})
        if rows:
            return pd.DataFrame(rows)
    return _generate_synthetic_msv(config)


@st.cache_data(ttl=3600, show_spinner="Loading DMA data…")
def load_dma_msv_data(config_json: str, dma_codes_json: str = "[]") -> pd.DataFrame:
    config = _config_from_json(config_json)
    dma_codes = json.loads(dma_codes_json) if dma_codes_json else []
    return _generate_synthetic_dma_msv(config, dma_codes=dma_codes or None)


@st.cache_data(ttl=3600)
def load_share_of_search(config_json: str) -> pd.DataFrame:
    config = _config_from_json(config_json)
    msv_df = load_msv_data(config_json)
    return compute_share_of_search(msv_df, config.brand_keyword)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3 — APP LAYOUT
# ═══════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Brand Awareness Tracker",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

_inject_signal_deck_css()


# ── Session state ────────────────────────────────────────────────────────

def _init():
    defaults = {
        "ba_configured": False, "ba_config": None, "ba_step": 1,
        "ba_brand_name": "", "ba_brand_domain": "", "ba_competitors": [],
        "ba_geo_scope": "national", "ba_dma_selections": [], "ba_interval": "monthly",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()


# ── Sidebar ──────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(f"""
<div style="padding:0.75rem 0.5rem 1rem;border-bottom:1px solid {C['glass_border']};margin-bottom:1rem;">
  <div style="display:flex;align-items:center;gap:0.5rem;">
    <div style="width:2rem;height:2rem;border-radius:8px;
    background:linear-gradient(135deg,{C['accent']},{C['accent_dark']});
    display:flex;align-items:center;justify-content:center;
    font-size:0.9rem;">📡</div>
    <div>
      <div style="font-size:0.95rem;font-weight:700;color:{C['text']};
      letter-spacing:-0.02em;">Brand Awareness</div>
      <div style="font-size:0.6rem;color:{C['text3']};font-weight:500;
      letter-spacing:0.06em;text-transform:uppercase;">MSV TRACKER</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    if st.session_state.ba_configured:
        config: TrackerConfig = st.session_state.ba_config
        st.markdown(f"""
<div style="padding:0.5rem;background:{C['surface']};border-radius:10px;
border:1px solid {C['glass_border']};margin-bottom:0.75rem;">
  <div style="font-size:0.6rem;color:{C['text3']};text-transform:uppercase;
  letter-spacing:0.06em;font-weight:600;margin-bottom:0.3rem;">Active Tracker</div>
  <div style="font-size:0.8rem;font-weight:600;color:{C['text']};">{config.brand_name}</div>
  <div style="font-size:0.65rem;color:{C['text2']};margin-top:0.15rem;">
  {len(config.competitors)} peers · {config.geo_scope.title()} · {config.interval.title()}</div>
</div>""", unsafe_allow_html=True)

        api_color = C["positive"] if SEMRUSH_API_KEY else C["warning"]
        api_label = "SEMrush Live" if SEMRUSH_API_KEY else "Synthetic Data"
        st.markdown(f"""
<div style="display:flex;align-items:center;gap:0.4rem;padding:0.3rem 0.5rem;">
  <div style="width:6px;height:6px;border-radius:50%;background:{api_color};"></div>
  <span style="font-size:0.65rem;color:{C['text2']};">{api_label}</span>
</div>""", unsafe_allow_html=True)

        if st.button("↻ Reconfigure", key="sidebar_reconfig", use_container_width=True):
            st.session_state.ba_configured = False
            st.session_state.ba_config = None
            st.session_state.ba_step = 1
            st.rerun()
    else:
        st.markdown(f"""
<div style="font-size:0.7rem;color:{C['text2']};padding:0 0.5rem;">
Configure a brand tracker to get started. Enter your brand, select competitors,
and choose your tracking scope.</div>""", unsafe_allow_html=True)


# ── Page header ──────────────────────────────────────────────────────────

st.markdown(f"""
<div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.25rem;">
  <span style="font-size:0.7rem;color:{C['text3']};">Brand Awareness</span>
  <span style="font-size:0.65rem;color:{C['text3']};">›</span>
  <span style="font-size:0.7rem;color:{C['text2']};">
  {'Dashboard' if st.session_state.ba_configured else f'Setup · Step {st.session_state.ba_step} of 3'}</span>
</div>""", unsafe_allow_html=True)

st.markdown(f"""
<h1 style="font-size:1.6rem;font-weight:700;color:{C['text']};margin:0 0 1rem 0;
letter-spacing:-0.02em;">Brand Awareness Tracker</h1>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4 — WIZARD FLOW
# ═══════════════════════════════════════════════════════════════════════════

def _load_fitb_preset():
    config = default_fitb_config()
    st.session_state.ba_config = config
    st.session_state.ba_configured = True
    st.session_state.ba_step = 4
    st.session_state.ba_brand_name = config.brand_name
    st.session_state.ba_brand_domain = config.brand_domain
    st.session_state.ba_competitors = config.competitors


def _render_progress(step: int):
    """Render wizard progress bar."""
    steps = ["Enter Brand", "Select Competitors", "Configure Tracking"]
    html = '<div style="display:flex;gap:0.5rem;margin-bottom:1.25rem;align-items:center;">'
    for i, name in enumerate(steps, 1):
        if i < step:
            color, icon = C["positive"], "✓"
        elif i == step:
            color, icon = C["accent"], str(i)
        else:
            color, icon = C["text3"], str(i)
        weight = "600" if i == step else "400"
        html += (
            f'<div style="display:flex;align-items:center;gap:0.3rem;">'
            f'<div style="width:1.5rem;height:1.5rem;border-radius:50%;background:{color};'
            f'color:{C["bg"]};font-size:0.65rem;font-weight:700;display:flex;'
            f'align-items:center;justify-content:center;">{icon}</div>'
            f'<span style="font-size:0.72rem;color:{color};font-weight:{weight};">{name}</span>'
            f'</div>')
        if i < len(steps):
            html += f'<div style="width:2.5rem;height:1px;background:{C["border"]};"></div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def _step_1():
    _render_progress(1)
    card_start("Enter Your Brand", "Start by entering your brand name and domain")

    col1, col2 = st.columns(2)
    with col1:
        brand_name = st.text_input("Brand Name", value=st.session_state.ba_brand_name,
                                    placeholder="e.g. Fifth Third Bank", key="s1_name")
    with col2:
        brand_domain = st.text_input("Brand Domain", value=st.session_state.ba_brand_domain,
                                      placeholder="e.g. 53.com", key="s1_domain")

    st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
    btn = st.columns([1, 1, 3])
    with btn[0]:
        if st.button("Next →", key="s1_next", type="primary",
                      disabled=not (brand_name and brand_domain)):
            st.session_state.ba_brand_name = brand_name
            st.session_state.ba_brand_domain = brand_domain
            st.session_state.ba_brand_keyword = brand_name.lower()
            st.session_state.ba_step = 2
            st.rerun()
    with btn[1]:
        if st.button("Load FITB Preset", key="s1_fitb"):
            _load_fitb_preset()
            st.rerun()

    card_end()


def _step_2():
    _render_progress(2)
    card_start("Select Competitors", f"Peer set for {st.session_state.ba_brand_name}")

    recommendations = recommend_competitors(
        st.session_state.ba_brand_domain, st.session_state.ba_brand_name)

    st.markdown(
        f"<div style='font-size:0.72rem;color:{C['text2']};margin-bottom:0.5rem;'>"
        f"Recommended based on {'SEMrush organic analysis' if SEMRUSH_API_KEY else 'known peer groups'}. "
        f"Toggle to include/exclude, or add custom entries below.</div>",
        unsafe_allow_html=True)

    preset_name = st.selectbox("Load Peer Group Preset",
                                ["Custom"] + list(PEER_PRESETS.keys()), key="s2_preset")
    if preset_name != "Custom":
        recommendations = PEER_PRESETS[preset_name]

    selected = []
    cols = st.columns(2)
    for i, comp in enumerate(recommendations):
        with cols[i % 2]:
            if st.checkbox(f"{comp['name']} ({comp['domain']})", value=True, key=f"s2_c{i}"):
                selected.append(comp)

    st.markdown("---")
    st.markdown(f"<div style='font-size:0.65rem;font-weight:600;text-transform:uppercase;"
                f"color:{C['text2']};letter-spacing:0.06em;margin-bottom:0.25rem;'>"
                f"Add Custom Competitor</div>", unsafe_allow_html=True)
    cc = st.columns([2, 2, 2, 1])
    with cc[0]:
        cn = st.text_input("Name", key="s2_cn", placeholder="e.g. Ally Bank")
    with cc[1]:
        ck = st.text_input("Keyword", key="s2_ck", placeholder="e.g. ally bank")
    with cc[2]:
        cd = st.text_input("Domain", key="s2_cd", placeholder="e.g. ally.com")
    with cc[3]:
        st.markdown("<div style='height:1.75rem;'></div>", unsafe_allow_html=True)
        if st.button("Add", key="s2_add") and cn and ck:
            selected.append({"name": cn, "keyword": ck, "domain": cd or ""})

    st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
    btn = st.columns([1, 1, 3])
    with btn[0]:
        if st.button("← Back", key="s2_back"):
            st.session_state.ba_step = 1
            st.rerun()
    with btn[1]:
        if st.button("Next →", key="s2_next", type="primary", disabled=len(selected) == 0):
            st.session_state.ba_competitors = selected
            st.session_state.ba_step = 3
            st.rerun()

    card_end()


def _step_3():
    _render_progress(3)
    card_start("Configure Tracking", "Set geographic scope and tracking frequency")

    col1, col2 = st.columns(2)
    with col1:
        geo = st.radio("Geographic Scope", ["National", "National + DMA/Footprint"],
                        key="s3_geo",
                        help="National = SEMrush country-level. DMA adds footprint-level (Google Ads, future).")
        geo_scope = "dma" if "DMA" in geo else "national"
    with col2:
        interval = st.selectbox("Tracking Interval",
                                 ["Monthly", "Weekly", "Daily", "Quarterly"], key="s3_int")

    dma_selections = []
    if geo_scope == "dma":
        dma_options = [f"{v[0]}" for v in _DMA_WEIGHTS.values()]
        dma_selections = st.multiselect("Select DMAs / Footprint Markets",
                                         dma_options, default=dma_options[:6], key="s3_dma")

    st.markdown("---")
    ac = st.columns(2)
    with ac[0]:
        s_color = C["positive"] if SEMRUSH_API_KEY else C["warning"]
        s_label = "Connected" if SEMRUSH_API_KEY else "Not configured — synthetic data"
        st.markdown(f"<div style='font-size:0.72rem;color:{C['text2']};'>"
                    f"<span style='color:{s_color};'>●</span> SEMrush API: {s_label}</div>",
                    unsafe_allow_html=True)
    with ac[1]:
        st.markdown(f"<div style='font-size:0.72rem;color:{C['text2']};'>"
                    f"<span style='color:{C['critical']};'>●</span> Google Ads API: Not yet integrated</div>",
                    unsafe_allow_html=True)

    st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
    btn = st.columns([1, 1, 3])
    with btn[0]:
        if st.button("← Back", key="s3_back"):
            st.session_state.ba_step = 2
            st.rerun()
    with btn[1]:
        if st.button("Run Tracker →", key="s3_run", type="primary"):
            config = TrackerConfig(
                brand_name=st.session_state.ba_brand_name,
                brand_keyword=getattr(st.session_state, "ba_brand_keyword",
                                       st.session_state.ba_brand_name.lower()),
                brand_domain=st.session_state.ba_brand_domain,
                competitors=st.session_state.ba_competitors,
                geo_scope=geo_scope,
                dma_codes=[],
                interval=interval.lower(),
            )
            st.session_state.ba_config = config
            st.session_state.ba_configured = True
            st.session_state.ba_step = 4
            st.rerun()

    card_end()


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5 — DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════

def _render_dashboard():
    config: TrackerConfig = st.session_state.ba_config
    cj = config_to_json(config)

    # Status bar
    api_badge = "SEMrush Live" if SEMRUSH_API_KEY else "Synthetic"
    st.markdown(
        f"<div style='font-size:0.68rem;color:{C['text3']};margin-bottom:0.75rem;'>"
        f"Tracking <strong style='color:{C['text']};'>{config.brand_name}</strong> "
        f"vs {len(config.competitors)} peers · {config.geo_scope.title()} · "
        f"{config.interval.title()} · Data: {api_badge}</div>",
        unsafe_allow_html=True)

    msv_df = load_msv_data(cj)
    sos_df = load_share_of_search(cj)

    # ── KPI Strip ────────────────────────────────────────────────────────
    card_start("Brand Awareness KPIs", f"{config.brand_name} vs peer set · latest month")

    latest = sos_df.iloc[-1] if not sos_df.empty else None
    prior = sos_df.iloc[-2] if len(sos_df) > 1 else None

    if latest is not None:
        k = st.columns(5)
        with k[0]:
            bmsv = int(latest["brand_msv"])
            pmsv = int(prior["brand_msv"]) if prior is not None else bmsv
            kpi_card("Brand MSV", bmsv, delta=bmsv - pmsv,
                     delta_pct=((bmsv - pmsv) / pmsv * 100) if pmsv else 0)
        with k[1]:
            share = float(latest["share_of_search"]) * 100
            pshare = float(prior["share_of_search"]) * 100 if prior is not None else share
            kpi_card("Share of Search", share, fmt="percent", delta=share - pshare)
        with k[2]:
            rank = int(latest["rank"])
            pc = len(config.competitors) + 1
            st.markdown(f"""
<div style="background:{C['glass_bg']};border:1px solid {C['glass_border']};
border-radius:12px;padding:0.8rem 1rem;backdrop-filter:blur(8px);">
  <div style="font-size:0.6rem;font-weight:600;text-transform:uppercase;
  letter-spacing:0.06em;color:{C['text2']};margin-bottom:0.25rem;">Peer Rank</div>
  <div style="font-size:1.5rem;font-weight:700;color:{C['text']};
  font-family:{FONT_MONO};font-variant-numeric:tabular-nums;">
  #{rank}<span style="font-size:0.75rem;color:{C['text3']};font-weight:400;">/{pc}</span></div>
</div>""", unsafe_allow_html=True)
        with k[3]:
            tmsv = int(latest["total_msv"])
            ptmsv = int(prior["total_msv"]) if prior is not None else tmsv
            kpi_card("Total Peer MSV", tmsv, delta=tmsv - ptmsv)
        with k[4]:
            months = msv_df["date"].nunique()
            freshness = msv_df["date"].max()
            f_str = freshness.strftime("%b %Y") if hasattr(freshness, "strftime") else str(freshness)
            st.markdown(f"""
<div style="background:{C['glass_bg']};border:1px solid {C['glass_border']};
border-radius:12px;padding:0.8rem 1rem;backdrop-filter:blur(8px);">
  <div style="font-size:0.6rem;font-weight:600;text-transform:uppercase;
  letter-spacing:0.06em;color:{C['text2']};margin-bottom:0.25rem;">Data Coverage</div>
  <div style="font-size:1.5rem;font-weight:700;color:{C['text']};
  font-family:{FONT_MONO};font-variant-numeric:tabular-nums;">
  {months}<span style="font-size:0.7rem;color:{C['text3']};font-weight:400;"> months</span></div>
  <div style="font-size:0.6rem;color:{C['text3']};margin-top:0.15rem;">Latest: {f_str}</div>
</div>""", unsafe_allow_html=True)

    card_end()

    # ── MSV Trend ────────────────────────────────────────────────────────
    card_start("Monthly Search Volume Trend", "Branded keyword search volume — all peers")

    fig = go.Figure()
    brands_sorted = msv_df.groupby("brand")["msv"].mean().sort_values(ascending=False).index.tolist()

    for i, brand in enumerate(brands_sorted):
        bd = msv_df[msv_df["brand"] == brand].sort_values("date")
        is_own = (brand == config.brand_name)
        color = C["accent"] if is_own else CHART_PALETTE[i % len(CHART_PALETTE)]
        fig.add_trace(go.Scatter(
            x=bd["date"].tolist(), y=bd["msv"].tolist(),
            mode="lines", name=brand,
            line=dict(color=color, width=3.5 if is_own else 1.8),
            opacity=1.0 if is_own else 0.6,
            hovertemplate=f"<b>{brand}</b><br>Date: %{{x|%b %Y}}<br>MSV: %{{y:,.0f}}<extra></extra>",
        ))

    plotly_layout(fig, 420)
    fig.update_layout(
        xaxis=dict(tickformat="%b '%y", dtick="M3"),
        yaxis=dict(title="Monthly Search Volume", separatethousands=True),
    )
    st.plotly_chart(fig, use_container_width=True, key="msv_trend")
    card_end()

    # ── Share of Search ──────────────────────────────────────────────────
    card_start("Share of Search",
               "Brand's share of total branded search in peer set — awareness proxy (Les Binet / IPA)")

    tabs = st.tabs(["Brand SoS Trend", "All Brands Stacked"])

    with tabs[0]:
        if not sos_df.empty:
            fig_sos = go.Figure()
            fig_sos.add_trace(go.Scatter(
                x=sos_df["date"].tolist(),
                y=(sos_df["share_of_search"] * 100).tolist(),
                mode="lines+markers", name=f"{config.brand_name} Share",
                line=dict(color=C["accent"], width=3),
                marker=dict(size=6, color=C["accent"]),
                fill="tozeroy", fillcolor="rgba(52,225,212,0.10)",
                hovertemplate=f"<b>{config.brand_name}</b><br>%{{x|%b %Y}}<br>Share: %{{y:.1f}}%<extra></extra>",
            ))
            plotly_layout(fig_sos, 320)
            fig_sos.update_layout(
                xaxis=dict(tickformat="%b '%y", dtick="M3"),
                yaxis=dict(title="Share of Search %", ticksuffix="%", rangemode="tozero"),
                showlegend=False,
            )
            st.plotly_chart(fig_sos, use_container_width=True, key="sos_trend")

    with tabs[1]:
        if not msv_df.empty:
            share_data = []
            for date, grp in msv_df.groupby("date"):
                total = grp["msv"].sum()
                for _, row in grp.iterrows():
                    share_data.append({"date": date, "brand": row["brand"],
                                        "share": (row["msv"] / total * 100) if total > 0 else 0})
            sdf = pd.DataFrame(share_data)
            brands_by_share = sdf.groupby("brand")["share"].mean().sort_values().index.tolist()

            fig_st = go.Figure()
            for i, brand in enumerate(brands_by_share):
                bd = sdf[sdf["brand"] == brand].sort_values("date")
                is_own = (brand == config.brand_name)
                color = C["accent"] if is_own else CHART_PALETTE[i % len(CHART_PALETTE)]
                fig_st.add_trace(go.Scatter(
                    x=bd["date"].tolist(), y=bd["share"].tolist(),
                    mode="lines", name=brand, stackgroup="one",
                    line=dict(width=0.5, color=color),
                    hovertemplate=f"<b>{brand}</b><br>Share: %{{y:.1f}}%<extra></extra>",
                ))
            plotly_layout(fig_st, 360)
            fig_st.update_layout(
                xaxis=dict(tickformat="%b '%y", dtick="M3"),
                yaxis=dict(title="Share %", ticksuffix="%", range=[0, 100]),
            )
            st.plotly_chart(fig_st, use_container_width=True, key="stacked_share")

    card_end()

    # ── Peer Comparison Table ────────────────────────────────────────────
    card_start("Peer Comparison", "Latest month — ranked by Monthly Search Volume")

    comp_df = compute_peer_comparison(msv_df)
    if not comp_df.empty:
        display = comp_df.copy()
        display["MSV"] = display["msv"].apply(lambda v: f"{v:,}")
        display["Share"] = display["share"].apply(lambda v: f"{v:.1f}%")
        display["Rank"] = display["rank"]
        display["MSV Δ"] = display["msv_delta"].apply(
            lambda v: f"{'▲' if v > 0 else '▼'} {abs(v):,}" if v != 0 else "—")
        display["Share Δ"] = display["share_delta"].apply(
            lambda v: f"{'▲' if v > 0 else '▼'} {abs(v):.1f}pp" if abs(v) > 0.05 else "—")
        display["Brand"] = display.apply(
            lambda r: f"→ {r['brand']}" if r["keyword"] == config.brand_keyword else r["brand"], axis=1)
        st.dataframe(display[["Rank", "Brand", "MSV", "Share", "MSV Δ", "Share Δ"]],
                     use_container_width=True, hide_index=True,
                     height=min(420, 50 + len(display) * 38))
    else:
        st.info("No comparison data available.")

    card_end()

    # ── DMA Breakdown ────────────────────────────────────────────────────
    if config.geo_scope == "dma":
        card_start("DMA / Footprint Breakdown",
                   "Branded search volume by market — synthetic (Google Ads API pending)")

        dma_df = load_dma_msv_data(cj)
        if not dma_df.empty:
            latest_dt = dma_df["date"].max()
            own = dma_df[(dma_df["keyword"] == config.brand_keyword) &
                         (dma_df["date"] == latest_dt)].copy()
            if not own.empty:
                own = own.sort_values("msv", ascending=True)
                labels = own["dma_name"].tolist() if "dma_name" in own.columns else own["geo"].tolist()

                fig_dma = go.Figure()
                fig_dma.add_trace(go.Bar(
                    y=labels, x=own["msv"].tolist(), orientation="h",
                    marker=dict(color=C["accent"], line=dict(width=0)),
                    hovertemplate="<b>%{y}</b><br>MSV: %{x:,.0f}<extra></extra>",
                ))
                plotly_layout(fig_dma, max(300, len(labels) * 35))
                fig_dma.update_layout(
                    xaxis=dict(title="Monthly Search Volume", separatethousands=True),
                    yaxis=dict(tickfont=dict(color=C["text"])),
                    margin=dict(l=120, r=20, t=10, b=40),
                )
                st.plotly_chart(fig_dma, use_container_width=True, key="dma_bars")

            with st.expander("DMA Detail Table", expanded=False):
                detail = []
                for geo in dma_df["geo"].unique():
                    gl = dma_df[(dma_df["geo"] == geo) & (dma_df["date"] == latest_dt)]
                    total = gl["msv"].sum()
                    br = gl[gl["keyword"] == config.brand_keyword]
                    if not br.empty:
                        bmsv = int(br["msv"].iloc[0])
                        dn = br["dma_name"].iloc[0] if "dma_name" in br.columns else geo
                        detail.append({"DMA": dn, "Brand MSV": f"{bmsv:,}",
                                        "Total Peer MSV": f"{int(total):,}",
                                        "Share": f"{bmsv/total*100:.1f}%" if total else "—"})
                if detail:
                    st.dataframe(pd.DataFrame(detail), use_container_width=True, hide_index=True)
        else:
            st.info("No DMA data available.")

        card_end()


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6 — RENDER
# ═══════════════════════════════════════════════════════════════════════════

if st.session_state.ba_configured and st.session_state.ba_step == 4:
    _render_dashboard()
else:
    step = st.session_state.ba_step
    if step == 1:
        _step_1()
    elif step == 2:
        _step_2()
    elif step == 3:
        _step_3()
