"""Unit tests for Product & Experience Pydantic models (APE-20a).

Covers ProductInitiative, RoadmapItem, ABTest, TestingVelocity:
  - required fields and types
  - enum validation
  - numeric constraints
  - cross-field validators (model_validators)
  - optional field handling
  - ApexBase inheritance (id, created_at)
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.models.ab_test import ABTest, ABTestStatus
from src.models.product_initiative import (
    InitiativePriority,
    InitiativeStatus,
    ProductInitiative,
)
from src.models.roadmap_item import RoadmapItem, RoadmapPriority, RoadmapStatus
from src.models.testing_velocity import TestingVelocity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _initiative(**overrides) -> dict:
    base = {
        "title": "Digital Account Opening v3",
        "description": "Redesign the digital account opening flow",
        "status": InitiativeStatus.in_progress,
        "priority": InitiativePriority.p0,
        "product_area": "checking",
        "owner": "Sarah Chen",
        "target_launch_date": date(2026, 6, 1),
        "hypothesis": "Simplified form reduces abandonment by 20%",
        "success_metric": "application_completion_rate",
        "baseline_value": Decimal("0.4200"),
        "target_value": Decimal("0.5100"),
    }
    base.update(overrides)
    return base


def _roadmap(**overrides) -> dict:
    from uuid import uuid4
    base = {
        "initiative_id": uuid4(),
        "quarter": "2026-Q2",
        "title": "Form Simplification — Phase 1",
        "status": RoadmapStatus.in_flight,
        "team": "Product Engineering",
        "effort_points": 8,
        "priority": RoadmapPriority.must_have,
    }
    base.update(overrides)
    return base


def _abtest(**overrides) -> dict:
    base = {
        "test_name": "DAOv3 Short Form vs Long Form",
        "hypothesis": "Shorter form reduces drop-off",
        "product_area": "checking",
        "status": ABTestStatus.running,
        "variant_count": 2,
        "start_date": date(2026, 4, 1),
        "sample_size": 20000,
        "traffic_allocation_pct": Decimal("0.5000"),
        "primary_metric": "application_completion_rate",
        "control_rate": Decimal("0.420000"),
    }
    base.update(overrides)
    return base


def _velocity(**overrides) -> dict:
    base = {
        "week_start": date(2026, 4, 28),
        "team": "Product Growth",
        "tests_launched": 2,
        "tests_completed": 1,
        "tests_running": 3,
        "winner_rate": Decimal("0.5000"),
        "avg_test_duration_days": 21,
        "total_sample_size": 35000,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# ProductInitiative
# ---------------------------------------------------------------------------

class TestProductInitiative:

    def test_valid_initiative_creates(self):
        pi = ProductInitiative(**_initiative())
        assert pi.title == "Digital Account Opening v3"
        assert pi.status == "in_progress"
        assert pi.priority == "p0"

    def test_inherits_apex_base(self):
        pi = ProductInitiative(**_initiative())
        assert pi.id is not None
        assert pi.created_at is not None

    def test_all_statuses_accepted(self):
        for s in ("discovery", "in_progress", "launched", "paused", "cancelled"):
            pi = ProductInitiative(**_initiative(status=s))
            assert pi.status == s

    def test_invalid_status_rejected(self):
        with pytest.raises(Exception):
            ProductInitiative(**_initiative(status="archived"))

    def test_all_priorities_accepted(self):
        for p in ("p0", "p1", "p2", "p3"):
            pi = ProductInitiative(**_initiative(priority=p))
            assert pi.priority == p

    def test_invalid_priority_rejected(self):
        with pytest.raises(Exception):
            ProductInitiative(**_initiative(priority="p4"))

    def test_actual_launch_date_optional(self):
        pi = ProductInitiative(**_initiative())
        assert pi.actual_launch_date is None

    def test_actual_launch_date_set(self):
        pi = ProductInitiative(**_initiative(actual_launch_date=date(2026, 6, 14)))
        assert pi.actual_launch_date == date(2026, 6, 14)

    def test_actual_value_optional(self):
        pi = ProductInitiative(**_initiative())
        assert pi.actual_value is None

    def test_actual_value_set(self):
        pi = ProductInitiative(**_initiative(actual_value=Decimal("0.5340")))
        assert pi.actual_value == Decimal("0.5340")

    def test_baseline_and_target_stored(self):
        pi = ProductInitiative(**_initiative())
        assert pi.baseline_value == Decimal("0.4200")
        assert pi.target_value == Decimal("0.5100")


# ---------------------------------------------------------------------------
# RoadmapItem
# ---------------------------------------------------------------------------

class TestRoadmapItem:

    def test_valid_item_creates(self):
        ri = RoadmapItem(**_roadmap())
        assert ri.quarter == "2026-Q2"
        assert ri.effort_points == 8

    def test_inherits_apex_base(self):
        ri = RoadmapItem(**_roadmap())
        assert ri.id is not None

    def test_all_statuses_accepted(self):
        for s in ("planned", "in_flight", "complete", "deferred"):
            ri = RoadmapItem(**_roadmap(status=s))
            assert ri.status == s

    def test_invalid_status_rejected(self):
        with pytest.raises(Exception):
            RoadmapItem(**_roadmap(status="cancelled"))

    def test_all_priorities_accepted(self):
        for p in ("must_have", "should_have", "nice_to_have"):
            ri = RoadmapItem(**_roadmap(priority=p))
            assert ri.priority == p

    def test_invalid_priority_rejected(self):
        with pytest.raises(Exception):
            RoadmapItem(**_roadmap(priority="critical"))

    def test_effort_points_min_1(self):
        with pytest.raises(Exception):
            RoadmapItem(**_roadmap(effort_points=0))

    def test_effort_points_max_21(self):
        ri = RoadmapItem(**_roadmap(effort_points=21))
        assert ri.effort_points == 21

    def test_effort_points_above_21_rejected(self):
        with pytest.raises(Exception):
            RoadmapItem(**_roadmap(effort_points=22))

    def test_invalid_quarter_format_rejected(self):
        with pytest.raises(Exception):
            RoadmapItem(**_roadmap(quarter="Q2-2026"))

    def test_valid_quarters_accepted(self):
        for q in ("2024-Q1", "2026-Q4", "2028-Q3"):
            ri = RoadmapItem(**_roadmap(quarter=q))
            assert ri.quarter == q

    def test_milestone_optional(self):
        ri = RoadmapItem(**_roadmap())
        assert ri.milestone is None

    def test_milestone_set(self):
        ri = RoadmapItem(**_roadmap(milestone="Beta"))
        assert ri.milestone == "Beta"


# ---------------------------------------------------------------------------
# ABTest
# ---------------------------------------------------------------------------

class TestABTest:

    def test_valid_test_creates(self):
        t = ABTest(**_abtest())
        assert t.test_name == "DAOv3 Short Form vs Long Form"
        assert t.variant_count == 2

    def test_inherits_apex_base(self):
        t = ABTest(**_abtest())
        assert t.id is not None

    def test_all_statuses_accepted(self):
        for s in ("draft", "running", "complete", "stopped"):
            t = ABTest(**_abtest(status=s))
            assert t.status == s

    def test_invalid_status_rejected(self):
        with pytest.raises(Exception):
            ABTest(**_abtest(status="archived"))

    def test_variant_count_min_2(self):
        with pytest.raises(Exception):
            ABTest(**_abtest(variant_count=1))

    def test_variant_count_max_5(self):
        t = ABTest(**_abtest(variant_count=5))
        assert t.variant_count == 5

    def test_variant_count_above_5_rejected(self):
        with pytest.raises(Exception):
            ABTest(**_abtest(variant_count=6))

    def test_traffic_allocation_must_be_0_to_1(self):
        with pytest.raises(Exception):
            ABTest(**_abtest(traffic_allocation_pct=Decimal("1.01")))

    def test_end_date_before_start_rejected(self):
        with pytest.raises(Exception):
            ABTest(**_abtest(
                start_date=date(2026, 4, 1),
                end_date=date(2026, 3, 1),
            ))

    def test_end_date_equal_start_accepted(self):
        t = ABTest(**_abtest(start_date=date(2026, 4, 1), end_date=date(2026, 4, 1)))
        assert t.end_date == t.start_date

    def test_optional_outcome_fields_none_by_default(self):
        t = ABTest(**_abtest())
        assert t.treatment_rate is None
        assert t.lift_pct is None
        assert t.p_value is None
        assert t.is_significant is None
        assert t.winner is None

    def test_complete_test_with_outcomes(self):
        t = ABTest(**_abtest(
            status="complete",
            end_date=date(2026, 5, 1),
            treatment_rate=Decimal("0.512000"),
            lift_pct=Decimal("0.2190"),
            p_value=Decimal("0.0012"),
            is_significant=True,
            winner="treatment_a",
        ))
        assert t.is_significant is True
        assert t.winner == "treatment_a"

    def test_p_value_range_0_to_1(self):
        with pytest.raises(Exception):
            ABTest(**_abtest(p_value=Decimal("1.01")))


# ---------------------------------------------------------------------------
# TestingVelocity
# ---------------------------------------------------------------------------

class TestTestingVelocity:

    def test_valid_velocity_creates(self):
        tv = TestingVelocity(**_velocity())
        assert tv.tests_running == 3
        assert tv.winner_rate == Decimal("0.5000")

    def test_inherits_apex_base(self):
        tv = TestingVelocity(**_velocity())
        assert tv.id is not None

    def test_winner_rate_0_accepted(self):
        tv = TestingVelocity(**_velocity(winner_rate=Decimal("0.0000")))
        assert tv.winner_rate == Decimal("0.0000")

    def test_winner_rate_1_accepted(self):
        tv = TestingVelocity(**_velocity(winner_rate=Decimal("1.0000")))
        assert tv.winner_rate == Decimal("1.0000")

    def test_winner_rate_above_1_rejected(self):
        with pytest.raises(Exception):
            TestingVelocity(**_velocity(winner_rate=Decimal("1.01")))

    def test_completed_exceeds_launched_plus_running_rejected(self):
        # launched=1, running=1 → max completed = 2; passing 3 must fail
        with pytest.raises(Exception):
            TestingVelocity(**_velocity(tests_launched=1, tests_running=1, tests_completed=3))

    def test_completed_equals_launched_plus_running_accepted(self):
        tv = TestingVelocity(**_velocity(tests_launched=2, tests_running=1, tests_completed=3))
        assert tv.tests_completed == 3

    def test_negative_tests_launched_rejected(self):
        with pytest.raises(Exception):
            TestingVelocity(**_velocity(tests_launched=-1))

    def test_sample_size_required_non_negative(self):
        with pytest.raises(Exception):
            TestingVelocity(**_velocity(total_sample_size=-1))
