"""TestingVelocity — weekly snapshot of experimentation throughput for the Product team."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import Field, model_validator

from src.models.base import ApexBase


class TestingVelocity(ApexBase):
    """Weekly experimentation velocity snapshot for a product team."""

    week_start: date
    team: str
    tests_launched: int = Field(ge=0)
    tests_completed: int = Field(ge=0)
    tests_running: int = Field(ge=0)
    winner_rate: Decimal = Field(ge=0, le=1, decimal_places=4)
    avg_test_duration_days: int = Field(ge=0)
    total_sample_size: int = Field(ge=0)

    @model_validator(mode="after")
    def completed_lte_launched_plus_running(self) -> "TestingVelocity":
        # Completed tests in a given week can't exceed all tests ever in flight
        if self.tests_completed > self.tests_launched + self.tests_running:
            raise ValueError(
                "tests_completed cannot exceed tests_launched + tests_running"
            )
        return self
