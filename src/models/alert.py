from datetime import datetime
from typing import Optional

from .base import ApexBase


class Alert(ApexBase):
    title: str
    severity: str  # "info", "warning", "critical"
    category: str  # "performance", "budget", "competitor", "system"
    message: str
    is_read: bool = False
    resolved_at: Optional[datetime] = None
