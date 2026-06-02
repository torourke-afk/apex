"""
Recalibrate funnel_summary_daily.csv:
1. Brand UOI (brand_interactions) → 1-1.5M per week (~143K-214K per day across 10 DMAs)
2. SEM fields → sync with recalibrated sem_daily.csv
3. Keep everything else unchanged
"""

import numpy as np
import pandas as pd

np.random.seed(42)

DATA_DIR = "/sessions/festive-beautiful-johnson/mnt/second-brain/output/synthetic-banking-dataset"

# Load existing funnel data
fdf = pd.read_csv(f"{DATA_DIR}/funnel_summary_daily.csv")
sem_df = pd.read_csv(f"{DATA_DIR}/sem_daily.csv")

print(f"Funnel rows: {len(fdf)}")
print(f"SEM rows: {len(sem_df)}")

# ---------------------------------------------------------------------------
# 1. Sync SEM fields from recalibrated sem_daily.csv
# ---------------------------------------------------------------------------
sem_daily_agg = sem_df.groupby(["date", "dma_id"]).agg(
    sem_impressions=("impressions", "sum"),
    sem_clicks=("clicks", "sum"),
    sem_spend=("spend", "sum"),
).reset_index()

# Merge into funnel
fdf = fdf.drop(columns=["sem_impressions", "sem_clicks", "sem_spend"])
fdf = fdf.merge(sem_daily_agg, on=["date", "dma_id"], how="left")
fdf["sem_impressions"] = fdf["sem_impressions"].fillna(0).astype(int)
fdf["sem_clicks"] = fdf["sem_clicks"].fillna(0).astype(int)
fdf["sem_spend"] = fdf["sem_spend"].fillna(0.0).round(2)

# ---------------------------------------------------------------------------
# 2. Recalibrate Brand UOI (brand_interactions)
# ---------------------------------------------------------------------------
# Target: 1-1.5M per week = ~178K per day across all DMAs
# That's ~17.8K per DMA per day on average
# Current: ~706 per DMA per day — need ~25x multiplier

# Brand UOI = people who engaged with brand media (clicked, viewed, interacted)
# This should be proportional to brand_impressions (but much smaller)
# With ~594K brand_impressions per DMA per day, 17.8K interactions = ~3% interaction rate

# Use brand_impressions as the base and apply a realistic interaction rate
# Interaction rate varies by DMA size and day
TARGET_WEEKLY_UOI = 1_250_000  # middle of 1M-1.5M range
TARGET_DAILY_UOI = TARGET_WEEKLY_UOI / 7  # ~178,571 per day across all DMAs

# DMA weights (same as SEM)
DMA_WEIGHTS = {
    "DMA_602": 0.16, "DMA_524": 0.14, "DMA_515": 0.13,
    "DMA_535": 0.11, "DMA_539": 0.11, "DMA_534": 0.09,
    "DMA_528": 0.08, "DMA_527": 0.07, "DMA_542": 0.06, "DMA_541": 0.05,
}

# Seasonality for brand (similar to SEM but smoother)
def brand_seasonality(date_str):
    date = pd.Timestamp(date_str)
    month = date.month
    seasonal = {1: 0.90, 2: 1.05, 3: 1.10, 4: 1.08, 5: 1.00,
                6: 0.92, 7: 0.88, 8: 0.90, 9: 0.95, 10: 1.05,
                11: 1.12, 12: 1.08}
    dow = date.dayofweek
    dow_mult = {0: 1.02, 1: 1.04, 2: 1.05, 3: 1.04, 4: 1.00,
                5: 0.90, 6: 0.82}
    return seasonal[month] * dow_mult[dow]

# Generate new brand_interactions
new_interactions = []
for _, row in fdf.iterrows():
    dma_w = DMA_WEIGHTS.get(row["dma_id"], 0.05)
    s_mult = brand_seasonality(row["date"])
    base = TARGET_DAILY_UOI * dma_w * s_mult
    # Add noise ±12%
    val = base * np.random.uniform(0.88, 1.12)
    new_interactions.append(max(100, int(val)))

fdf["brand_interactions"] = new_interactions

# ---------------------------------------------------------------------------
# Reorder columns to match original
# ---------------------------------------------------------------------------
col_order = [
    "date", "dma_id", "dma_name",
    "brand_impressions", "brand_interactions", "brand_spend",
    "sem_impressions", "sem_clicks", "sem_spend",
    "social_impressions", "social_clicks", "social_spend",
    "display_impressions", "display_clicks", "display_spend",
    "site_sessions", "site_bounce_rate", "product_page_views",
    "applications_started", "applications_submitted",
    "applications_approved", "accounts_funded", "total_initial_deposits",
]
fdf = fdf[col_order]

# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------
print("\n=== Recalibrated Brand UOI ===")
daily_uoi = fdf.groupby("date").brand_interactions.sum()
print(f"Brand interactions per day (all DMAs): avg={daily_uoi.mean():,.0f}, "
      f"min={daily_uoi.min():,.0f}, max={daily_uoi.max():,.0f}")
weekly_uoi = fdf.copy()
weekly_uoi["week"] = pd.to_datetime(weekly_uoi["date"]).dt.isocalendar().week
weekly_sums = weekly_uoi.groupby("week").brand_interactions.sum()
print(f"Brand interactions per week: avg={weekly_sums.mean():,.0f}, "
      f"min={weekly_sums.min():,.0f}, max={weekly_sums.max():,.0f}")

print("\n=== Recalibrated SEM fields ===")
daily_sem = fdf.groupby("date").agg({"sem_impressions": "sum", "sem_clicks": "sum", "sem_spend": "sum"})
print(f"SEM impressions per day: {daily_sem.sem_impressions.mean():,.0f}")
print(f"SEM clicks per day: {daily_sem.sem_clicks.mean():,.0f}")
print(f"SEM spend per day: ${daily_sem.sem_spend.mean():,.0f}")
print(f"SEM annual spend: ${fdf.sem_spend.sum():,.0f}")

# Save
output_path = f"{DATA_DIR}/funnel_summary_daily.csv"
fdf.to_csv(output_path, index=False)
print(f"\nSaved to {output_path}")
