from datetime import date
from decimal import Decimal
from typing import Optional

from .base import ApexBase


class Campaign(ApexBase):
    name: str
    channel: str
    status: str  # "draft", "active", "paused", "completed"
    spend: Decimal
    revenue: Decimal
    start_date: date
    end_date: Optional[date] = None
