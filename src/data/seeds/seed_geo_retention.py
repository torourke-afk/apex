"""Seed: Geographic Retention Data

Generates ~600 rows: ~50 US MSAs × 12 monthly periods.
90-day retention rates: 82–96%, correlated with market tier.
Uses real lat/lon coordinates for major US metropolitan areas.

Idempotent: DELETE + INSERT on geo_retention.

Run:
    python -m src.data.seeds.seed_geo_retention
"""

from __future__ import annotations

import os
import sys
import uuid

import numpy as np
import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema, Check

WORKSPACE = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if WORKSPACE not in sys.path:
    sys.path.insert(0, WORKSPACE)

from src.data.init_db import get_connection  # noqa: E402
from src.data.seeds._dates import TWELVE_MONTH_STRINGS  # noqa: E402

SEED = 42
rng = np.random.default_rng(SEED)

PERIODS = TWELVE_MONTH_STRINGS

# 50 US MSAs with verified lat/lon and market tier
# Tier 1: top 15 markets, Tier 2: mid 20, Tier 3: smaller 15
MSA_DATA = [
    # (geography, lat, lon, market_tier)
    # --- Tier 1 (top markets, highest retention) ---
    ("New York-Newark, NY-NJ",         40.712800, -74.006000, "tier_1"),
    ("Los Angeles-Long Beach, CA",     34.052200, -118.243700, "tier_1"),
    ("Chicago, IL",                    41.878100, -87.629800, "tier_1"),
    ("Dallas-Fort Worth, TX",          32.776700, -96.797000, "tier_1"),
    ("Houston, TX",                    29.760400, -95.369800, "tier_1"),
    ("Washington, DC-VA-MD",           38.907200, -77.036900, "tier_1"),
    ("Philadelphia, PA",               39.952600, -75.165200, "tier_1"),
    ("Atlanta, GA",                    33.749000, -84.388000, "tier_1"),
    ("Miami, FL",                      25.774300, -80.193900, "tier_1"),
    ("Phoenix, AZ",                    33.448400, -112.074000, "tier_1"),
    ("Boston, MA",                     42.360100, -71.058800, "tier_1"),
    ("Riverside-San Bernardino, CA",   33.953500, -117.396200, "tier_1"),
    ("Seattle, WA",                    47.606200, -122.332100, "tier_1"),
    ("Minneapolis-St. Paul, MN",       44.977800, -93.265400, "tier_1"),
    ("San Diego, CA",                  32.715300, -117.157300, "tier_1"),
    # --- Tier 2 (mid markets) ---
    ("Tampa-St. Petersburg, FL",       27.950600, -82.457400, "tier_2"),
    ("Denver, CO",                     39.739200, -104.984900, "tier_2"),
    ("Portland, OR",                   45.523100, -122.676200, "tier_2"),
    ("St. Louis, MO",                  38.627000, -90.199400, "tier_2"),
    ("Baltimore, MD",                  39.290400, -76.612300, "tier_2"),
    ("San Antonio, TX",                29.424100, -98.493600, "tier_2"),
    ("Austin, TX",                     30.267200, -97.743100, "tier_2"),
    ("Charlotte, NC",                  35.227100, -80.843100, "tier_2"),
    ("Nashville, TN",                  36.174500, -86.767800, "tier_2"),
    ("Columbus, OH",                   39.961200, -82.998700, "tier_2"),
    ("Cincinnati, OH",                 39.103100, -84.512000, "tier_2"),
    ("Indianapolis, IN",               39.768400, -86.158100, "tier_2"),
    ("Cleveland, OH",                  41.499700, -81.694900, "tier_2"),
    ("Las Vegas, NV",                  36.174700, -115.136500, "tier_2"),
    ("Kansas City, MO",                39.099700, -94.578600, "tier_2"),
    ("Sacramento, CA",                 38.581600, -121.494400, "tier_2"),
    ("San Jose, CA",                   37.339400, -121.894900, "tier_2"),
    ("Pittsburgh, PA",                 40.440600, -79.995900, "tier_2"),
    ("Salt Lake City, UT",             40.760800, -111.891000, "tier_2"),
    ("Richmond, VA",                   37.540700, -77.436100, "tier_2"),
    # --- Tier 3 (smaller markets) ---
    ("Oklahoma City, OK",              35.467600, -97.516700, "tier_3"),
    ("Jacksonville, FL",               30.332200, -81.655700, "tier_3"),
    ("Memphis, TN",                    35.149700, -90.048800, "tier_3"),
    ("Louisville, KY",                 38.252700, -85.758500, "tier_3"),
    ("Hartford, CT",                   41.763700, -72.685100, "tier_3"),
    ("Birmingham, AL",                 33.520700, -86.802300, "tier_3"),
    ("New Orleans, LA",                29.951100, -90.071500, "tier_3"),
    ("Buffalo, NY",                    42.886400, -78.878400, "tier_3"),
    ("Providence, RI",                 41.824000, -71.412800, "tier_3"),
    ("Raleigh-Durham, NC",             35.779600, -78.638200, "tier_3"),
    ("Tucson, AZ",                     32.253500, -110.911800, "tier_3"),
    ("Fresno, CA",                     36.739700, -119.787200, "tier_3"),
    ("Omaha, NE",                      41.256500, -95.934500, "tier_3"),
    ("Albuquerque, NM",                35.084500, -106.650900, "tier_3"),
    ("Tulsa, OK",                      36.153900, -95.992800, "tier_3"),
]

assert len(MSA_DATA) == 50

# Tier → retention_90d center rates (within 82–96% overall)
TIER_RETENTION_CENTER = {
    "tier_1": 0.930,   # 93%
    "tier_2": 0.900,   # 90%
    "tier_3": 0.865,   # 86.5%
}
RETENTION_STD = 0.018
TREND_PER_MONTH = 0.001


def build_geo_retention() -> pd.DataFrame:
    rows = []
    now = pd.Timestamp.now()

    for geo, lat, lon, tier in MSA_DATA:
        # Stable per-MSA offset (±2% to create market heterogeneity)
        msa_offset = float(rng.uniform(-0.02, 0.02))
        for period_idx, period in enumerate(PERIODS):
            trend = period_idx * TREND_PER_MONTH
            center = TIER_RETENTION_CENTER[tier] + msa_offset + trend
            noise = float(rng.normal(0, RETENTION_STD))
            retention_90d = float(np.clip(center + noise, 0.82, 0.96))

            rows.append({
                "id":           str(uuid.uuid4()),
                "geography":    geo,
                "lat":          round(lat, 6),
                "lon":          round(lon, 6),
                "retention_90d": round(retention_90d, 4),
                "market_tier":  tier,
                "period":       period,
                "created_at":   now,
                "updated_at":   now,
            })

    return pd.DataFrame(rows)


GEO_SCHEMA = DataFrameSchema(
    {
        "id":           Column(str, nullable=False),
        "geography":    Column(str, nullable=False),
        "lat":          Column(float, Check.in_range(-90, 90)),
        "lon":          Column(float, Check.in_range(-180, 180)),
        "retention_90d": Column(float, Check.in_range(0.82, 0.96)),
        "market_tier":  Column(str, Check.isin(["tier_1", "tier_2", "tier_3"])),
        "period":       Column(str, nullable=False),
    },
    checks=[
        Check(lambda df: len(df) == 600, error="Expected exactly 600 rows (50 MSAs × 12 periods)"),
        Check(lambda df: df["geography"].nunique() == 50, error="Expected 50 unique MSAs"),
        # Tier 1 avg > Tier 3 avg
        Check(
            lambda df: (
                df[df["market_tier"] == "tier_1"]["retention_90d"].mean()
                > df[df["market_tier"] == "tier_3"]["retention_90d"].mean()
            ),
            error="Tier 1 retention should exceed Tier 3 on average",
        ),
        # Valid US lat/lon bounds
        Check(lambda df: df["lat"].between(24, 50).all(), error="Latitudes out of continental US range"),
        Check(lambda df: df["lon"].between(-130, -65).all(), error="Longitudes out of continental US range"),
    ],
    coerce=True,
)


def seed(verbose: bool = True) -> pd.DataFrame:
    df = build_geo_retention()

    df["lat"] = df["lat"].astype(float)
    df["lon"] = df["lon"].astype(float)
    df["retention_90d"] = df["retention_90d"].astype(float)

    GEO_SCHEMA.validate(df)

    conn = get_connection()
    try:
        conn.execute("DELETE FROM geo_retention")
        conn.register("geo_df", df)
        conn.execute("""
            INSERT INTO geo_retention
                (id, geography, lat, lon, retention_90d, market_tier,
                 period, created_at, updated_at)
            SELECT id, geography, lat, lon, retention_90d, market_tier,
                   period, created_at, updated_at
            FROM geo_df
        """)
        conn.commit()
    finally:
        try:
            conn.unregister("geo_df")
        except Exception:
            pass
        conn.close()

    if verbose:
        print(f"[seed_geo_retention] Inserted {len(df):,} rows into geo_retention")
        print(f"  MSAs: {df['geography'].nunique()}")
        print(f"  Periods: {df['period'].nunique()}")
        for tier in ["tier_1", "tier_2", "tier_3"]:
            grp = df[df["market_tier"] == tier]
            print(f"  {tier}: retention {grp['retention_90d'].min():.1%}–"
                  f"{grp['retention_90d'].max():.1%} "
                  f"(avg {grp['retention_90d'].mean():.1%})")

    return df


if __name__ == "__main__":
    seed()
