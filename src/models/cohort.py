from datetime import date
from typing import Any, Dict

from .base import ApexBase


class Cohort(ApexBase):
    name: str
    segment: str  # "new_customers", "returning", "high_value"
    criteria: Dict[str, Any]
    size: int
    period_start: date
    period_end: date
