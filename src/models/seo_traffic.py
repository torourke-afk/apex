"""SEOTraffic — weekly organic session and account traffic by product category.

Captures organic search traffic volume, account-level engagement, and
bounce rate for a product category per week.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import Field

from src.models.base import ApexBase


class SEOTraffic(ApexBase):
    """Organic traffic summary for a product category in a given week."""

    product_category: str = Field(min_length=1, description="Product category receiving organic traffic")
    week_start: date = Field(description="ISO date for the Monday of the tracking week")
    organic_sessions: int = Field(ge=0, description="Total organic search sessions")
    organic_accounts: int = Field(ge=0, description="Unique account-level visitors from organic search")
    bounce_rate: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("1"),
        decimal_places=4,
        description="Bounce rate as a proportion (0.0–1.0)",
    )
