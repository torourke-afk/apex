"""MoverMarketing — new-mover pipeline quality and conversion for one geo/period.

Tracks pipeline volume, propensity scores, and high-income sub-segment
performance for the new-mover acquisition program.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import Field

from src.models.base import ApexBase


class MoverMarketing(ApexBase):
    """New-mover marketing performance for one geography in one period."""

    geo: str = Field(min_length=1)
    period: date

    pipeline_volume: int = Field(ge=0)
    pipeline_quality_score: Decimal = Field(ge=0, le=100, decimal_places=2)
    mover_to_account_cvr: Decimal = Field(ge=0, le=1, decimal_places=6)
    propensity_benchmark: Decimal = Field(ge=0, decimal_places=2, description="Expected 3–5× industry benchmark")

    is_expansion_geo: bool = Field(description="True = newly added geo in current wave")

    high_income_subset_cvr: Decimal = Field(ge=0, le=1, decimal_places=6)
    high_income_subset_volume: int = Field(ge=0)
