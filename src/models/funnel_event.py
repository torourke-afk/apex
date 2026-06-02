from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from .base import ApexBase


class FunnelEvent(ApexBase):
    campaign_id: UUID
    stage: str  # "impression", "click", "lead", "mql", "sql", "opportunity", "closed_won"
    event_date: date
    count: int
    value: Optional[Decimal] = None
