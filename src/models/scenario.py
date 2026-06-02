from decimal import Decimal
from typing import Any, Dict, Optional

from .base import ApexBase


class Scenario(ApexBase):
    name: str
    description: Optional[str] = None
    base_budget: Decimal
    parameters: Dict[str, Any]
    results: Optional[Dict[str, Any]] = None
    status: str = "draft"  # "draft", "running", "completed"
