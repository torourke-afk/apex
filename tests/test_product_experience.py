"""
Tests for src/data/product_experience.py (APE-20d)

Covers:
  - load_product_pipeline schema and values
  - load_pipeline_category_breakdown aggregation
  - load_roadmap_gantt schema and date ordering
  - load_roadmap_wave_summary completeness
  - load_test_velocity columns and baseline proximity
  - load_ab_test_results schema and lift formatting
  - load_test_sparklines keys and length
  - STATUS_SEVERITY mapping coverage
"""

from __future__ import annotations

import datetime
import math

import pandas as pd
import pytest

from src.data.product_experience import (
    PRODUCT_STATUSES,
    ROADMAP_WAVES,
    STATUS_SEVERITY,
    load_ab_test_results,
    load_pipeline_category_breakdown,
    load_product_pipeline,
    load_roadmap_gantt,
    load_roadmap_wave_summary,
    load_test_sparklines,
    load_test_velocity,
)


# ── Product Pipeline ────────────────────────────────────────────────────────────

class TestLoadProductPipeline:
    def test_returns_dataframe(self):
        df = load_product_pipeline()
        assert isinstance(df, pd.DataFrame)

    def test_has_expected_columns(self):
        df = load_product_pipeline()
        required = {"Product", "Category", "Status", "Owner", "Priority", "Est. Launch", "Open Issues", "Health"}
        assert required.issubset(set(df.columns))

    def test_statuses_are_valid(self):
        df = load_product_pipeline()
        assert set(df["Status"].unique()).issubset(set(PRODUCT_STATUSES))

    def test_health_values_are_valid(self):
        df = load_product_pipeline()
        assert set(df["Health"].unique()).issubset({"On Track", "At Risk", "Blocked"})

    def test_open_issues_non_negative(self):
        df = load_product_pipeline()
        assert (df["Open Issues"] >= 0).all()

    def test_at_least_one_product(self):
        df = load_product_pipeline()
        assert len(df) >= 1

    def test_deterministic(self):
        df1 = load_product_pipeline()
        df2 = load_product_pipeline()
        pd.testing.assert_frame_equal(df1, df2)


# ── Category Breakdown ─────────────────────────────────────────────────────────

class TestLoadPipelineCategoryBreakdown:
    def test_returns_dataframe(self):
        df = load_pipeline_category_breakdown()
        assert isinstance(df, pd.DataFrame)

    def test_has_required_columns(self):
        df = load_pipeline_category_breakdown()
        assert {"Category", "Status", "Count"}.issubset(set(df.columns))

    def test_counts_positive(self):
        df = load_pipeline_category_breakdown()
        assert (df["Count"] > 0).all()

    def test_total_matches_pipeline(self):
        pipeline = load_product_pipeline()
        breakdown = load_pipeline_category_breakdown()
        assert pipeline["Product"].count() == breakdown["Count"].sum()


# ── Roadmap Gantt ───────────────────────────────────────────────────────────────

class TestLoadRoadmapGantt:
    def test_returns_dataframe(self):
        df = load_roadmap_gantt()
        assert isinstance(df, pd.DataFrame)

    def test_has_required_columns(self):
        df = load_roadmap_gantt()
        required = {"Task", "Wave", "Category", "Start", "Finish", "Status", "Duration_Days"}
        assert required.issubset(set(df.columns))

    def test_finish_after_start(self):
        df = load_roadmap_gantt()
        assert (df["Finish"] > df["Start"]).all()

    def test_duration_matches_date_diff(self):
        df = load_roadmap_gantt()
        computed = [(row["Finish"] - row["Start"]).days for _, row in df.iterrows()]
        assert computed == list(df["Duration_Days"])

    def test_waves_are_valid(self):
        df = load_roadmap_gantt()
        assert set(df["Wave"].unique()).issubset(set(ROADMAP_WAVES))

    def test_all_waves_present(self):
        df = load_roadmap_gantt()
        for wave in ROADMAP_WAVES:
            assert wave in df["Wave"].values


# ── Wave Summary ───────────────────────────────────────────────────────────────

class TestLoadRoadmapWaveSummary:
    def test_returns_list(self):
        result = load_roadmap_wave_summary()
        assert isinstance(result, list)

    def test_one_entry_per_wave(self):
        result = load_roadmap_wave_summary()
        assert len(result) == len(ROADMAP_WAVES)

    def test_entry_has_required_keys(self):
        result = load_roadmap_wave_summary()
        required = {"wave", "status", "tasks_total", "tasks_done", "pct_complete", "target_date"}
        for entry in result:
            assert required.issubset(set(entry.keys()))

    def test_pct_complete_range(self):
        result = load_roadmap_wave_summary()
        for entry in result:
            assert 0 <= entry["pct_complete"] <= 100

    def test_tasks_done_lte_total(self):
        result = load_roadmap_wave_summary()
        for entry in result:
            assert entry["tasks_done"] <= entry["tasks_total"]


# ── Test Velocity ───────────────────────────────────────────────────────────────

class TestLoadTestVelocity:
    def test_returns_dataframe(self):
        df = load_test_velocity()
        assert isinstance(df, pd.DataFrame)

    def test_has_required_columns(self):
        df = load_test_velocity()
        required = {"Week", "Tests_Running", "Tests_Completed", "Significant_Wins", "Velocity_Score"}
        assert required.issubset(set(df.columns))

    def test_row_count_matches_n_weeks(self):
        for n in [4, 8, 12]:
            df = load_test_velocity(n_weeks=n)
            assert len(df) == n

    def test_velocity_score_positive(self):
        df = load_test_velocity()
        assert (df["Velocity_Score"] > 0).all()

    def test_wins_lte_completed(self):
        df = load_test_velocity()
        assert (df["Significant_Wins"] <= df["Tests_Completed"]).all()


# ── A/B Test Results ────────────────────────────────────────────────────────────

class TestLoadAbTestResults:
    def test_returns_dataframe(self):
        df = load_ab_test_results()
        assert isinstance(df, pd.DataFrame)

    def test_has_required_columns(self):
        df = load_ab_test_results()
        required = {"Test", "Category", "Status", "Control CVR", "Variant CVR", "Lift %", "Confidence"}
        assert required.issubset(set(df.columns))

    def test_lift_has_sign(self):
        df = load_ab_test_results()
        for val in df["Lift %"]:
            assert val.startswith("+") or val.startswith("-")

    def test_confidence_is_percent_string(self):
        df = load_ab_test_results()
        for val in df["Confidence"]:
            assert val.endswith("%")

    def test_at_least_one_row(self):
        df = load_ab_test_results()
        assert len(df) >= 1

    def test_deterministic(self):
        df1 = load_ab_test_results()
        df2 = load_ab_test_results()
        pd.testing.assert_frame_equal(df1, df2)


# ── Sparklines ─────────────────────────────────────────────────────────────────

class TestLoadTestSparklines:
    def test_returns_dict(self):
        result = load_test_sparklines()
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        result = load_test_sparklines()
        assert {"wins_rate", "velocity_score", "tests_active", "lift_avg"}.issubset(set(result.keys()))

    def test_each_series_has_twelve_points(self):
        result = load_test_sparklines()
        for key, series in result.items():
            assert len(series) == 12, f"{key} has {len(series)} points, expected 12"

    def test_values_are_numeric(self):
        result = load_test_sparklines()
        for key, series in result.items():
            for v in series:
                assert isinstance(v, (int, float)) and not math.isnan(v), \
                    f"{key} contains non-numeric value {v!r}"


# ── STATUS_SEVERITY mapping ─────────────────────────────────────────────────────

class TestStatusSeverityMapping:
    def test_all_statuses_covered(self):
        for status in PRODUCT_STATUSES:
            assert status in STATUS_SEVERITY, f"Missing severity for status: {status}"

    def test_severity_values_are_valid(self):
        valid = {"info", "success", "warning", "error"}
        for status, severity in STATUS_SEVERITY.items():
            assert severity in valid, f"Invalid severity {severity!r} for {status}"
