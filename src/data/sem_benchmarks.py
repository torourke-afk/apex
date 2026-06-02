"""SEM benchmark constants (APE-89).

Canonical benchmark values derived from realistic search benchmarks.
Import from here — do not redefine in sem_loaders.py or elsewhere.

Google Brand:     CPC $0.45-$0.75, CTR 20-30%
Google Non-Brand: CPC $6.50-$15.00, CTR 5-10%
Google PMax:      CPC $1.15-$2.00, CTR 10-20%
Bing Brand:       CPC $0.15-$0.35, CTR 15-25%
Bing Non-Brand:   CPC $1.50-$5.00, CTR 2-5%
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------

# Total annual SEM budget (~$26M across Google + Bing)
SEM_ANNUAL_BUDGET: float = 26_000_000.0

# Budget share by intent type (brand 30%, non_brand 50%, pmax 20% on Google;
# brand 35%, non_brand 65% on Bing; Google 80%, Bing 20% overall)
SEM_BUDGET_SHARE: dict[str, float] = {
    "brand": 0.30,
    "non-brand": 0.53,    # google non-brand + bing non-brand combined
    "pmax": 0.17,
}

# ---------------------------------------------------------------------------
# CTR benchmarks  (blended Google+Bing midpoints)
# ---------------------------------------------------------------------------
SEM_CTR_BENCHMARK: dict[str, float] = {
    "brand": 0.247,         # Google 25% dominant; Bing 20%
    "non-brand": 0.072,     # Google 7.5%; Bing 3.5%
    "pmax": 0.145,          # Google only: 10-20%
}

# Google-specific benchmarks
SEM_CTR_GOOGLE: dict[str, float] = {
    "brand": 0.25,          # 20-30%
    "non-brand": 0.075,     # 5-10%
    "pmax": 0.15,           # 10-20%
}

# Bing-specific benchmarks
SEM_CTR_BING: dict[str, float] = {
    "brand": 0.20,          # 15-25%
    "non-brand": 0.035,     # 2-5%
}

# ---------------------------------------------------------------------------
# CVR benchmarks  (conversion rates)
# ---------------------------------------------------------------------------
SEM_CVR_BENCHMARK: dict[str, float] = {
    "brand": 0.065,         # 5-8%
    "non-brand": 0.045,     # 3-6%
    "pmax": 0.055,          # 4-7%
}

# ---------------------------------------------------------------------------
# CPC benchmarks  (blended Google+Bing midpoints)
# ---------------------------------------------------------------------------
SEM_CPC_BENCHMARK: dict[str, float] = {
    "brand": 0.59,          # Google $0.60 dominant; Bing $0.24
    "non-brand": 10.13,     # Google $10.75; Bing $3.25
    "pmax": 1.54,           # Google only: $1.15-$2.00
}

# Google-specific benchmarks
SEM_CPC_GOOGLE: dict[str, float] = {
    "brand": 0.60,          # $0.45-$0.75
    "non-brand": 10.75,     # $6.50-$15.00
    "pmax": 1.58,           # $1.15-$2.00
}

# Bing-specific benchmarks
SEM_CPC_BING: dict[str, float] = {
    "brand": 0.25,          # $0.15-$0.35
    "non-brand": 3.25,      # $1.50-$5.00
}

# ---------------------------------------------------------------------------
# Quality score thresholds
# ---------------------------------------------------------------------------
SEM_QS_HEALTHY: int = 7           # QS >= 7 is considered healthy
SEM_QS_ALERT: int = 5             # QS <= 5 triggers negative keyword review
SEM_QS_NEGATIVE_DEFAULT: int = 6  # Default qs_threshold for load_sem_negative_keyword_score

# ---------------------------------------------------------------------------
# Impression share benchmarks
# ---------------------------------------------------------------------------
SEM_IS_BENCHMARK: dict[str, float] = {
    "brand": 0.83,          # 70-95% range
    "non-brand": 0.50,      # 35-65% range
    "pmax": 0.68,           # 55-80% range
}

# ---------------------------------------------------------------------------
# CPL benchmarks (Cost Per Lead = spend / conversions)
# ---------------------------------------------------------------------------
SEM_CPL_BENCHMARK: dict[str, float] = {
    "brand": 9.08,          # brand CPC / brand CVR
    "non-brand": 225.11,    # non-brand CPC / non-brand CVR
    "pmax": 28.00,          # pmax CPC / pmax CVR
}

# ---------------------------------------------------------------------------
# Flat aliases (spec-mandated public names)
# ---------------------------------------------------------------------------

# Composite benchmark dict — all per-metric, per-intent-type benchmarks
SEM_BENCHMARKS: dict = {
    "ctr": SEM_CTR_BENCHMARK,
    "cvr": SEM_CVR_BENCHMARK,
    "cpc": SEM_CPC_BENCHMARK,
    "impression_share": SEM_IS_BENCHMARK,
    "budget_share": SEM_BUDGET_SHARE,
}

# Alert thresholds used for monitoring and negative keyword scoring
SEM_ALERT_THRESHOLDS: dict = {
    "qs_healthy": SEM_QS_HEALTHY,
    "qs_alert": SEM_QS_ALERT,
    "qs_negative_default": SEM_QS_NEGATIVE_DEFAULT,
}
