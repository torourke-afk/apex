"""Centralized date anchors for seed data generation.

All seed modules import from here so synthetic data is always "live"
relative to the current date. Yesterday is always the latest data point.
"""
from datetime import date, datetime, timedelta, timezone

# The latest data point is always yesterday
YESTERDAY = date.today() - timedelta(days=1)
TODAY = date.today()
NOW = datetime.now(timezone.utc)

# Common windows
TRAILING_90D_START = YESTERDAY - timedelta(days=89)
TRAILING_90D_END = YESTERDAY

TRAILING_30D_START = YESTERDAY - timedelta(days=29)
TRAILING_30D_END = YESTERDAY

# 12-month window ending on the 1st of the current month
# e.g. if today is July 16, 2026: months run from Aug 2025 through Jul 2026
import pandas as pd
TWELVE_MONTH_STARTS = pd.date_range(
    end=TODAY.replace(day=1), periods=12, freq="MS"
)
TWELVE_MONTH_STRINGS = [d.strftime("%Y-%m") for d in TWELVE_MONTH_STARTS]

# 12-week window ending yesterday
TWELVE_WEEK_START = YESTERDAY - timedelta(weeks=12) + timedelta(days=1)
TWELVE_WEEK_MONDAYS = pd.date_range(
    start=TWELVE_WEEK_START - timedelta(days=TWELVE_WEEK_START.weekday()),
    periods=12,
    freq="W-MON"
)

# Fiscal year (May 1 of current or prior year through Apr 30 next)
_fy_start_year = TODAY.year if TODAY.month >= 5 else TODAY.year - 1
FY_START = date(_fy_start_year, 5, 1)
FY_END = date(_fy_start_year + 1, 4, 30)
FY_MONTH_STARTS = pd.date_range(start=FY_START, end=FY_END, freq="MS")
