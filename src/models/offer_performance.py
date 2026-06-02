"""OfferPerformance — funnel and impact metrics for a retention/onboarding offer."""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field

from src.models.base import ApexBase


class OfferPerformance(ApexBase):
    """Tracks funnel conversion and 30/90-day P&L impact for a single offer."""

    offer_name: str
    eligibility_rate: Decimal = Field(ge=0, le=1, decimal_places=4)
    activation_rate: Decimal = Field(ge=0, le=1, decimal_places=4)
    fulfillment_rate: Decimal = Field(ge=0, le=1, decimal_places=4)
    day_30_impact: Decimal = Field(decimal_places=4, description="Net revenue impact at day 30 (can be negative during promo period)")
    day_90_impact: Decimal = Field(decimal_places=4, description="Net revenue impact at day 90")
    period: str = Field(
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="ISO month YYYY-MM",
    )
