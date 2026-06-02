"""SystemHealthCheck — Operations Command Center system health monitoring model.

Tracks the status of data pipelines, API integrations, and platform
connections that feed the Apex Command Center dashboards.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import Field

from src.models.base import ApexBase


class SystemStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


class SystemCategory(str, Enum):
    DATA_PIPELINE = "data_pipeline"
    API_INTEGRATION = "api_integration"
    PLATFORM_CONNECTION = "platform_connection"
    DATABASE = "database"
    REPORTING = "reporting"
    OTHER = "other"


class SystemHealthCheck(ApexBase):
    """A point-in-time health status record for a monitored system component."""

    system_name: str = Field(min_length=1, max_length=255, description="Component identifier")
    category: SystemCategory
    status: SystemStatus

    checked_at: datetime = Field(description="Timestamp of the health check (UTC)")
    response_time_ms: Optional[int] = Field(
        default=None, ge=0, description="Latency in milliseconds if applicable"
    )
    uptime_pct: Optional[Decimal] = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("100"),
        decimal_places=4,
        description="Rolling 30-day uptime percentage",
    )
    error_message: Optional[str] = Field(
        default=None, description="Error detail when status is degraded or down"
    )
    owner_team: Optional[str] = Field(
        default=None, description="Team responsible for this component"
    )
    last_incident_at: Optional[datetime] = Field(
        default=None, description="Timestamp of the last known incident"
    )
