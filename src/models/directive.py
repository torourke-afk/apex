from datetime import date
from typing import Optional

from .base import ApexBase


class Directive(ApexBase):
    title: str
    directive_type: str  # "strategic", "tactical", "operational"
    priority: str  # "high", "medium", "low"
    owner: str
    due_date: Optional[date] = None
    status: str  # "active", "completed", "cancelled"
    notes: Optional[str] = None
