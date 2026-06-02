"""BEIScore — Bank Engagement Index composite score with weighted validator.

Composite formula (weights must sum to 1.0):
  composite = 0.35 * direct_deposit_score
            + 0.25 * digital_adoption_score
            + 0.20 * cross_sell_score
            + 0.12 * product_depth_score
            + 0.08 * engagement_score
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from pydantic import Field, model_validator

from src.models.base import ApexBase

# Component → weight mapping (must sum to 1.0)
_WEIGHTS: dict[str, Decimal] = {
    "direct_deposit_score": Decimal("0.35"),
    "digital_adoption_score": Decimal("0.25"),
    "cross_sell_score": Decimal("0.20"),
    "product_depth_score": Decimal("0.12"),
    "engagement_score": Decimal("0.08"),
}
_TOLERANCE = Decimal("0.005")  # allow minor float rounding


class BEIScore(ApexBase):
    """Bank Engagement Index score for a market tier / period combination."""

    market_tier: str = Field(description="e.g. 'tier_1', 'tier_2', 'tier_3'")
    period: str = Field(
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="ISO month YYYY-MM",
    )

    # Component scores (0–100 scale)
    direct_deposit_score: Decimal = Field(ge=0, le=100, decimal_places=2)
    digital_adoption_score: Decimal = Field(ge=0, le=100, decimal_places=2)
    cross_sell_score: Decimal = Field(ge=0, le=100, decimal_places=2)
    product_depth_score: Decimal = Field(ge=0, le=100, decimal_places=2)
    engagement_score: Decimal = Field(ge=0, le=100, decimal_places=2)

    # Derived composite (0–100 scale)
    composite_score: Decimal = Field(ge=0, le=100, decimal_places=2)

    @model_validator(mode="after")
    def _validate_composite(self) -> "BEIScore":
        expected = sum(
            getattr(self, field) * weight
            for field, weight in _WEIGHTS.items()
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if abs(expected - self.composite_score) > _TOLERANCE:
            raise ValueError(
                f"composite_score {self.composite_score} does not match "
                f"weighted formula (expected {expected}). "
                f"Weights: {_WEIGHTS}"
            )
        return self
