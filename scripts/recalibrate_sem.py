"""
Recalibrate sem_daily.csv with realistic search benchmarks.

Changes:
1. Add search_engine column (google ~80% spend, bing ~20%)
2. Replace 'conquest' campaign_type with 'pmax' (Google only)
3. Recalibrate CPCs and CTRs to real benchmarks:
   Google Brand:     CPC $0.45-$0.75, CTR 20-30%
   Google Non-Brand: CPC $6.50-$15.00, CTR 5-10%
   Google PMax:      CPC $1.15-$2.00, CTR 10-20%
   Bing Brand:       CPC $0.15-$0.35, CTR 15-25%
   Bing Non-Brand:   CPC $1.50-$5.00, CTR 2-5%
4. Keep same campaign structure, products, DMAs, date range
5. Recalibrate impressions/clicks/spend to maintain realistic total SEM budget
"""

import numpy as np
import pandas as pd

np.random.seed(42)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATA_DIR = "/sessions/festive-beautiful-johnson/mnt/second-brain/output/synthetic-banking-dataset"

# Target annual SEM budget: ~$27M total (keeping roughly same as before)
# Google gets ~80%, Bing ~20%
GOOGLE_SHARE = 0.80
BING_SHARE = 0.20

# Products and their relative spend weights
PRODUCTS = {
    "CHK": 0.40,  # Checking — biggest product
    "SAV": 0.25,  # Savings
    "CD":  0.20,  # CD
    "MMA": 0.15,  # MMA
}

# Campaign type spend split (of each engine's budget)
# Google: brand 30%, non-brand 50%, pmax 20%
# Bing: brand 35%, non-brand 65% (no PMax on Bing)
GOOGLE_TYPE_SPLIT = {"brand": 0.30, "non-brand": 0.50, "pmax": 0.20}
BING_TYPE_SPLIT   = {"brand": 0.35, "non-brand": 0.65}

# Benchmark ranges: (cpc_min, cpc_max, ctr_min, ctr_max)
BENCHMARKS = {
    ("google", "brand"):     (0.45, 0.75, 0.20, 0.30),
    ("google", "non-brand"): (6.50, 15.00, 0.05, 0.10),
    ("google", "pmax"):      (1.15, 2.00, 0.10, 0.20),
    ("bing", "brand"):       (0.15, 0.35, 0.15, 0.25),
    ("bing", "non-brand"):   (1.50, 5.00, 0.02, 0.05),
}

# DMAs (same as original dataset)
DMAS = [
    ("DMA_515", "Cincinnati, OH"),
    ("DMA_524", "Atlanta, GA"),
    ("DMA_527", "Indianapolis, IN"),
    ("DMA_528", "Nashville, TN"),
    ("DMA_534", "Orlando, FL"),
    ("DMA_535", "Columbus, OH"),
    ("DMA_539", "Tampa, FL"),
    ("DMA_541", "Lexington, KY"),
    ("DMA_542", "Dayton, OH"),
    ("DMA_602", "Chicago, IL"),
]

# DMA relative weight (larger markets get more spend)
DMA_WEIGHTS = {
    "DMA_602": 0.16,  # Chicago
    "DMA_524": 0.14,  # Atlanta
    "DMA_515": 0.13,  # Cincinnati
    "DMA_535": 0.11,  # Columbus
    "DMA_539": 0.11,  # Tampa
    "DMA_534": 0.09,  # Orlando
    "DMA_528": 0.08,  # Nashville
    "DMA_527": 0.07,  # Indianapolis
    "DMA_542": 0.06,  # Dayton
    "DMA_541": 0.05,  # Lexington
}

# Date range
dates = pd.date_range("2025-01-01", "2025-12-31", freq="D")

# Seasonality multiplier (banking products)
def seasonality(date):
    month = date.month
    # Tax refund season (Feb-Apr) = boost, summer lull, Q4 holiday + CD rate season
    seasonal = {1: 0.95, 2: 1.10, 3: 1.15, 4: 1.10, 5: 1.00,
                6: 0.90, 7: 0.85, 8: 0.88, 9: 0.95, 10: 1.05,
                11: 1.10, 12: 1.05}
    dow = date.dayofweek
    # Weekday traffic is higher than weekend
    dow_mult = {0: 1.05, 1: 1.08, 2: 1.10, 3: 1.08, 4: 1.02,
                5: 0.75, 6: 0.65}
    return seasonal[month] * dow_mult[dow]

# Target annual spend ~$27M
ANNUAL_BUDGET = 27_000_000

# ---------------------------------------------------------------------------
# Build campaigns
# ---------------------------------------------------------------------------
# Google campaigns: brand + non-brand + pmax per product, plus General Banking
# Bing campaigns: brand + non-brand per product
campaigns = []

for prod, prod_weight in PRODUCTS.items():
    prod_upper = prod
    prod_name = {"CHK": "Checking", "SAV": "Savings", "CD": "CD", "MMA": "MMA"}[prod]

    # Google campaigns
    campaigns.append({
        "campaign_id": f"SEM_{prod_upper}_BRAND",
        "campaign_name": f"{prod_name} - Brand",
        "campaign_type": "brand",
        "product": prod_upper,
        "search_engine": "google",
        "budget_share": GOOGLE_SHARE * GOOGLE_TYPE_SPLIT["brand"] * prod_weight,
    })
    campaigns.append({
        "campaign_id": f"SEM_{prod_upper}_NB",
        "campaign_name": f"{prod_name} - Non-Brand",
        "campaign_type": "non-brand",
        "product": prod_upper,
        "search_engine": "google",
        "budget_share": GOOGLE_SHARE * GOOGLE_TYPE_SPLIT["non-brand"] * prod_weight,
    })
    campaigns.append({
        "campaign_id": f"SEM_{prod_upper}_PMAX",
        "campaign_name": f"{prod_name} - PMax",
        "campaign_type": "pmax",
        "product": prod_upper,
        "search_engine": "google",
        "budget_share": GOOGLE_SHARE * GOOGLE_TYPE_SPLIT["pmax"] * prod_weight,
    })

    # Bing campaigns
    campaigns.append({
        "campaign_id": f"BING_{prod_upper}_BRAND",
        "campaign_name": f"{prod_name} - Brand (Bing)",
        "campaign_type": "brand",
        "product": prod_upper,
        "search_engine": "bing",
        "budget_share": BING_SHARE * BING_TYPE_SPLIT["brand"] * prod_weight,
    })
    campaigns.append({
        "campaign_id": f"BING_{prod_upper}_NB",
        "campaign_name": f"{prod_name} - Non-Brand (Bing)",
        "campaign_type": "non-brand",
        "product": prod_upper,
        "search_engine": "bing",
        "budget_share": BING_SHARE * BING_TYPE_SPLIT["non-brand"] * prod_weight,
    })

# Add Google-only extras
campaigns.append({
    "campaign_id": "SEM_CD_RATE",
    "campaign_name": "CD - Rate Shoppers",
    "campaign_type": "non-brand",
    "product": "CD",
    "search_engine": "google",
    "budget_share": GOOGLE_SHARE * 0.03,  # Small extra non-brand budget
})
campaigns.append({
    "campaign_id": "SEM_GENERAL",
    "campaign_name": "General Banking",
    "campaign_type": "non-brand",
    "product": "CHK",
    "search_engine": "google",
    "budget_share": GOOGLE_SHARE * 0.02,  # Small catchall
})

# Normalize budget shares to sum to 1
total_share = sum(c["budget_share"] for c in campaigns)
for c in campaigns:
    c["budget_share"] /= total_share

print(f"Total campaigns: {len(campaigns)}")
for c in campaigns:
    print(f"  {c['campaign_id']:20s} {c['search_engine']:6s} {c['campaign_type']:10s} share={c['budget_share']:.4f}")

# ---------------------------------------------------------------------------
# Generate daily rows
# ---------------------------------------------------------------------------
rows = []
daily_budget = ANNUAL_BUDGET / 365

for date in dates:
    s_mult = seasonality(date)
    for dma_id, dma_name in DMAS:
        dma_w = DMA_WEIGHTS[dma_id]
        for camp in campaigns:
            engine = camp["search_engine"]
            ctype = camp["campaign_type"]
            cpc_min, cpc_max, ctr_min, ctr_max = BENCHMARKS[(engine, ctype)]

            # Daily spend for this campaign in this DMA
            base_spend = daily_budget * camp["budget_share"] * dma_w * s_mult
            # Add noise ±15%
            spend = base_spend * np.random.uniform(0.85, 1.15)

            # CPC with noise — higher impression share campaigns trend toward higher CPC
            cpc = np.random.uniform(cpc_min, cpc_max)

            # Clicks = spend / cpc
            clicks = max(1, int(spend / cpc))

            # CTR determines impressions
            ctr = np.random.uniform(ctr_min, ctr_max)
            impressions = max(clicks, int(clicks / ctr))

            # Recalculate actual CTR and spend
            actual_ctr = clicks / impressions if impressions > 0 else 0
            actual_spend = clicks * cpc

            # Impression share: brand higher, non-brand lower
            if ctype == "brand":
                imp_share = np.random.uniform(0.70, 0.95)
            elif ctype == "pmax":
                imp_share = np.random.uniform(0.55, 0.80)
            else:
                imp_share = np.random.uniform(0.35, 0.65)

            # Quality score: brand 7-10, non-brand 5-9, pmax 6-8
            if ctype == "brand":
                qs = round(np.random.uniform(7.0, 10.0), 1)
            elif ctype == "pmax":
                qs = round(np.random.uniform(6.0, 8.5), 1)
            else:
                qs = round(np.random.uniform(5.0, 9.0), 1)

            # Avg position: brand 1-2, non-brand 2-4, pmax 1-3
            if ctype == "brand":
                avg_pos = round(np.random.uniform(1.0, 2.0), 2)
            elif ctype == "pmax":
                avg_pos = round(np.random.uniform(1.0, 3.0), 2)
            else:
                avg_pos = round(np.random.uniform(1.5, 4.0), 2)

            # Conversions: brand 5-8% of clicks, non-brand 3-6%, pmax 4-7%
            if ctype == "brand":
                cvr = np.random.uniform(0.05, 0.08)
            elif ctype == "pmax":
                cvr = np.random.uniform(0.04, 0.07)
            else:
                cvr = np.random.uniform(0.03, 0.06)
            conversions = max(0, int(clicks * cvr))

            rows.append({
                "date": date.strftime("%Y-%m-%d"),
                "dma_id": dma_id,
                "dma_name": dma_name,
                "campaign_id": camp["campaign_id"],
                "campaign_name": camp["campaign_name"],
                "campaign_type": ctype,
                "search_engine": engine,
                "product": camp["product"],
                "impressions": impressions,
                "clicks": clicks,
                "ctr": round(actual_ctr, 6),
                "avg_cpc": round(cpc, 2),
                "spend": round(actual_spend, 2),
                "impression_share": round(imp_share, 4),
                "avg_position": avg_pos,
                "quality_score": qs,
                "conversions": conversions,
            })

df = pd.DataFrame(rows)

# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------
print(f"\nTotal rows: {len(df):,}")
print(f"Date range: {df.date.min()} - {df.date.max()}")
print(f"Total annual spend: ${df.spend.sum():,.0f}")
print(f"Unique campaigns: {df.campaign_id.nunique()}")
print()

print("=== Stats by search_engine + campaign_type ===")
for (eng, ct), g in df.groupby(["search_engine", "campaign_type"]):
    avg_cpc = g.spend.sum() / g.clicks.sum()
    avg_ctr = g.clicks.sum() / g.impressions.sum()
    print(f"  {eng:6s} {ct:10s}: spend=${g.spend.sum():>12,.0f}  "
          f"avg_cpc=${avg_cpc:.2f}  avg_ctr={avg_ctr:.1%}  "
          f"clicks={g.clicks.sum():>10,}  imps={g.impressions.sum():>12,}")

print()
print("=== Stats by search_engine ===")
for eng, g in df.groupby("search_engine"):
    print(f"  {eng}: spend=${g.spend.sum():,.0f} ({g.spend.sum()/df.spend.sum():.0%})")

# Save
output_path = f"{DATA_DIR}/sem_daily.csv"
df.to_csv(output_path, index=False)
print(f"\nSaved to {output_path}")
