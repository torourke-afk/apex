"""RetentionCohort — acquisition cohort retention metrics by channel/market/product."""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field, model_validator

from src.models.base import ApexBase


class RetentionCohort(ApexBase):
    """Retention and churn metrics for a single acquisition cohort slice."""

    # Cohort dimensions
    acquisition_month: str = Field(
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="ISO month YYYY-MM",
    )
    channel: str
    market: str
    offer_type: str
    product_mix: str
    quality_score_band: str  # e.g. "high", "mid", "low"

    # Time dimension
    mob: int = Field(ge=0, description="Months on books")

    # Metrics
    retention_rate: Decimal = Field(ge=0, le=1, decimal_places=4)
    active_accounts: int = Field(ge=0)
    churned_accounts: int = Field(ge=0)

    @model_validator(mode="after")
    def _retention_consistent(self) -> "RetentionCohort":
        total = self.active_accounts + self.churned_accounts
        if total > 0:
            implied = Decimal(self.active_accounts) / Decimal(total)
            delta = abs(implied - self.retention_rate)
            if delta > Decimal("0.01"):
                raise ValueError(
                    f"retention_rate {self.retention_rate} inconsistent with "
                    f"active/churned counts (implied {implied:.4f})"
                )
        return self
