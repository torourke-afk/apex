from datetime import date
from decimal import Decimal

from .base import ApexBase


class Budget(ApexBase):
    name: str
    channel: str
    period: str  # "monthly", "quarterly", "annual"
    period_start: date
    allocated: Decimal
    actual: Decimal
