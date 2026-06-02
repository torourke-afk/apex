"""
Industry Benchmark Rates — Full-Funnel Simulator
-------------------------------------------------
Baseline conversion rates for the 6 funnel transitions used in the waterfall
chart. Rates are float (0.0–1.0), representing the fraction of volume that
passes from one stage to the next.

Sources: blended financial-services digital acquisition benchmarks (RVGT 2024).
"""

# ---------------------------------------------------------------------------
# Funnel stage names (7 stages, 6 transitions)
# ---------------------------------------------------------------------------

FUNNEL_STAGES: list[str] = [
    "Visits",
    "Leads",
    "MQL",
    "App Started",
    "App Completed",
    "Approved",
    "Funded",
]

# Human-readable transition labels (length == len(FUNNEL_STAGES) - 1)
STAGE_TRANSITION_LABELS: list[str] = [
    "Visits → Leads",
    "Leads → MQL",
    "MQL → App Started",
    "App Started → Completed",
    "App Completed → Approved",
    "Approved → Funded",
]

# ---------------------------------------------------------------------------
# Benchmark conversion rates per transition
# Index 0 = Visits → Leads, index 5 = Approved → Funded
# ---------------------------------------------------------------------------

STAGE_RATES: list[float] = [
    0.035,   # Visits → Leads          (3.5% — industry average for financial services)
    0.400,   # Leads → MQL             (40% — marketing-qualified threshold)
    0.250,   # MQL → App Started       (25% — intent-to-apply conversion)
    0.650,   # App Started → Completed (65% — application completion)
    0.550,   # App Completed → Approved(55% — credit approval rate)
    0.700,   # Approved → Funded       (70% — funding take-up rate)
]

# Tolerance band for "at benchmark" classification (±2 percentage points)
BENCHMARK_TOLERANCE: float = 0.02
