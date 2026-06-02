from datetime import date
from decimal import Decimal
from typing import Optional

from .base import ApexBase


class Offer(ApexBase):
    name: str
    product: str
    offer_type: str  # "rate", "cashback", "fee_waiver", "bundle"
    value: Decimal
    start_date: date
    end_date: Optional[date] = None
    is_active: bool = True
