"""PFIMilestone — tracks PFI (Primary Financial Institution) onboarding milestones."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import Field

from src.models.base import ApexBase


class MilestoneType(str, Enum):
    direct_deposit = "direct_deposit"
    bill_pay = "bill_pay"
    debit_card = "debit_card"
    digital_wallet = "digital_wallet"
    p2p_payments = "p2p_payments"
    cross_sell = "cross_sell"


class SwitchingCost(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class PFIMilestone(ApexBase):
    """Tracks completion rates for each PFI onboarding milestone."""

    milestone_type: MilestoneType
    target_pct: Decimal = Field(ge=0, le=1, decimal_places=4)
    actual_pct: Decimal = Field(ge=0, le=1, decimal_places=4)
    target_days: int = Field(ge=1)
    tracking_source: str
    switching_cost: SwitchingCost
