"""SQLAlchemy ORM models for all Apex tables."""

import uuid
from datetime import datetime, date
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class Base(DeclarativeBase):
    pass


def _uuid_col(**kwargs):
    """Primary-key UUID column compatible with DuckDB and PostgreSQL."""
    return mapped_column(sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, **kwargs)


def _ts_col(nullable: bool = False, **kwargs):
    return mapped_column(sa.DateTime(), nullable=nullable, default=datetime.utcnow, **kwargs)


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = _uuid_col()
    name: Mapped[str] = mapped_column(sa.String(), nullable=False)
    channel: Mapped[str] = mapped_column(sa.String(), nullable=False)
    status: Mapped[str] = mapped_column(sa.String(), nullable=False, default="draft")
    spend: Mapped[Decimal] = mapped_column(sa.Numeric(18, 4), nullable=False, default=Decimal("0"))
    revenue: Mapped[Decimal] = mapped_column(sa.Numeric(18, 4), nullable=False, default=Decimal("0"))
    start_date: Mapped[date] = mapped_column(sa.Date(), nullable=False)
    end_date: Mapped[date | None] = mapped_column(sa.Date(), nullable=True)
    created_at: Mapped[datetime] = _ts_col()
    updated_at: Mapped[datetime] = _ts_col()


class FunnelEvent(Base):
    __tablename__ = "funnel_events"

    id: Mapped[uuid.UUID] = _uuid_col()
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("campaigns.id"),
        nullable=False,
    )
    stage: Mapped[str] = mapped_column(sa.String(), nullable=False)
    event_date: Mapped[date] = mapped_column(sa.Date(), nullable=False)
    count: Mapped[int] = mapped_column(sa.Integer(), nullable=False, default=0)
    value: Mapped[Decimal | None] = mapped_column(sa.Numeric(18, 4), nullable=True)
    created_at: Mapped[datetime] = _ts_col()
    updated_at: Mapped[datetime] = _ts_col()


class Cohort(Base):
    __tablename__ = "cohorts"

    id: Mapped[uuid.UUID] = _uuid_col()
    name: Mapped[str] = mapped_column(sa.String(), nullable=False)
    segment: Mapped[str] = mapped_column(sa.String(), nullable=False)
    criteria: Mapped[dict] = mapped_column(sa.JSON(), nullable=False, default=dict)
    size: Mapped[int] = mapped_column(sa.Integer(), nullable=False, default=0)
    period_start: Mapped[date] = mapped_column(sa.Date(), nullable=False)
    period_end: Mapped[date] = mapped_column(sa.Date(), nullable=False)
    created_at: Mapped[datetime] = _ts_col()
    updated_at: Mapped[datetime] = _ts_col()


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[uuid.UUID] = _uuid_col()
    name: Mapped[str] = mapped_column(sa.String(), nullable=False)
    product: Mapped[str] = mapped_column(sa.String(), nullable=False)
    offer_type: Mapped[str] = mapped_column(sa.String(), nullable=False)
    value: Mapped[Decimal] = mapped_column(sa.Numeric(18, 4), nullable=False)
    start_date: Mapped[date] = mapped_column(sa.Date(), nullable=False)
    end_date: Mapped[date | None] = mapped_column(sa.Date(), nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False, default=True)
    created_at: Mapped[datetime] = _ts_col()
    updated_at: Mapped[datetime] = _ts_col()


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = _uuid_col()
    title: Mapped[str] = mapped_column(sa.String(), nullable=False)
    severity: Mapped[str] = mapped_column(sa.String(), nullable=False, default="info")
    category: Mapped[str] = mapped_column(sa.String(), nullable=False)
    message: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    is_read: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(sa.DateTime(), nullable=True)
    created_at: Mapped[datetime] = _ts_col()
    updated_at: Mapped[datetime] = _ts_col()


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[uuid.UUID] = _uuid_col()
    name: Mapped[str] = mapped_column(sa.String(), nullable=False)
    channel: Mapped[str] = mapped_column(sa.String(), nullable=False)
    period: Mapped[str] = mapped_column(sa.String(), nullable=False)
    period_start: Mapped[date] = mapped_column(sa.Date(), nullable=False)
    allocated: Mapped[Decimal] = mapped_column(sa.Numeric(18, 4), nullable=False, default=Decimal("0"))
    actual: Mapped[Decimal] = mapped_column(sa.Numeric(18, 4), nullable=False, default=Decimal("0"))
    created_at: Mapped[datetime] = _ts_col()
    updated_at: Mapped[datetime] = _ts_col()


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[uuid.UUID] = _uuid_col()
    name: Mapped[str] = mapped_column(sa.String(), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text(), nullable=True)
    base_budget: Mapped[Decimal] = mapped_column(sa.Numeric(18, 4), nullable=False, default=Decimal("0"))
    parameters: Mapped[dict] = mapped_column(sa.JSON(), nullable=False, default=dict)
    results: Mapped[dict | None] = mapped_column(sa.JSON(), nullable=True)
    status: Mapped[str] = mapped_column(sa.String(), nullable=False, default="draft")
    created_at: Mapped[datetime] = _ts_col()
    updated_at: Mapped[datetime] = _ts_col()


class Directive(Base):
    __tablename__ = "directives"

    id: Mapped[uuid.UUID] = _uuid_col()
    title: Mapped[str] = mapped_column(sa.String(), nullable=False)
    directive_type: Mapped[str] = mapped_column(sa.String(), nullable=False)
    priority: Mapped[str] = mapped_column(sa.String(), nullable=False, default="medium")
    owner: Mapped[str] = mapped_column(sa.String(), nullable=False)
    due_date: Mapped[date | None] = mapped_column(sa.Date(), nullable=True)
    status: Mapped[str] = mapped_column(sa.String(), nullable=False, default="active")
    notes: Mapped[str | None] = mapped_column(sa.Text(), nullable=True)
    created_at: Mapped[datetime] = _ts_col()
    updated_at: Mapped[datetime] = _ts_col()


# ---------------------------------------------------------------------------
# Retention tables
# ---------------------------------------------------------------------------

class PfiMilestone(Base):
    __tablename__ = "pfi_milestones"

    id: Mapped[uuid.UUID] = _uuid_col()
    cohort_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("cohorts.id"),
        nullable=True,
    )
    milestone_type: Mapped[str] = mapped_column(sa.String(), nullable=False)
    target_pct: Mapped[Decimal] = mapped_column(sa.Numeric(6, 4), nullable=False)
    actual_pct: Mapped[Decimal] = mapped_column(sa.Numeric(6, 4), nullable=False)
    target_days: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    switching_cost: Mapped[Decimal] = mapped_column(sa.Numeric(18, 4), nullable=False)
    created_at: Mapped[datetime] = _ts_col()
    updated_at: Mapped[datetime] = _ts_col()


class CohortRetentionHeatmap(Base):
    __tablename__ = "cohort_retention_heatmap"

    id: Mapped[uuid.UUID] = _uuid_col()
    cohort_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("cohorts.id"),
        nullable=True,
    )
    acquisition_month: Mapped[str] = mapped_column(sa.String(), nullable=False)
    mob: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    retention_rate: Mapped[Decimal] = mapped_column(sa.Numeric(6, 4), nullable=False)
    channel: Mapped[str] = mapped_column(sa.String(), nullable=False)
    quality_score_band: Mapped[str] = mapped_column(sa.String(), nullable=False)
    market: Mapped[str] = mapped_column(sa.String(), nullable=False)
    offer_type: Mapped[str] = mapped_column(sa.String(), nullable=False)
    product_mix: Mapped[str] = mapped_column(sa.String(), nullable=False)
    created_at: Mapped[datetime] = _ts_col()
    updated_at: Mapped[datetime] = _ts_col()


class BeiScore(Base):
    __tablename__ = "bei_scores"

    id: Mapped[uuid.UUID] = _uuid_col()
    market_tier: Mapped[str] = mapped_column(sa.String(), nullable=False)
    period: Mapped[str] = mapped_column(sa.String(), nullable=False)
    ease_of_banking: Mapped[Decimal] = mapped_column(sa.Numeric(6, 4), nullable=False)
    trust: Mapped[Decimal] = mapped_column(sa.Numeric(6, 4), nullable=False)
    value_perception: Mapped[Decimal] = mapped_column(sa.Numeric(6, 4), nullable=False)
    digital_experience: Mapped[Decimal] = mapped_column(sa.Numeric(6, 4), nullable=False)
    service_quality: Mapped[Decimal] = mapped_column(sa.Numeric(6, 4), nullable=False)
    composite_score: Mapped[Decimal] = mapped_column(sa.Numeric(6, 4), nullable=False)
    created_at: Mapped[datetime] = _ts_col()
    updated_at: Mapped[datetime] = _ts_col()


class BehavioralTrigger(Base):
    __tablename__ = "behavioral_triggers"

    id: Mapped[uuid.UUID] = _uuid_col()
    trigger_name: Mapped[str] = mapped_column(sa.String(), nullable=False)
    condition: Mapped[str] = mapped_column(sa.String(), nullable=False)
    action: Mapped[str] = mapped_column(sa.String(), nullable=False)
    volume_per_week: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    conversion_rate: Mapped[Decimal] = mapped_column(sa.Numeric(6, 4), nullable=False)
    created_at: Mapped[datetime] = _ts_col()
    updated_at: Mapped[datetime] = _ts_col()


class GeoRetention(Base):
    __tablename__ = "geo_retention"

    id: Mapped[uuid.UUID] = _uuid_col()
    geography: Mapped[str] = mapped_column(sa.String(), nullable=False)
    lat: Mapped[Decimal] = mapped_column(sa.Numeric(9, 6), nullable=False)
    lon: Mapped[Decimal] = mapped_column(sa.Numeric(9, 6), nullable=False)
    retention_90d: Mapped[Decimal] = mapped_column(sa.Numeric(6, 4), nullable=False)
    market_tier: Mapped[str] = mapped_column(sa.String(), nullable=False)
    created_at: Mapped[datetime] = _ts_col()
    updated_at: Mapped[datetime] = _ts_col()


class OfferPerformance(Base):
    __tablename__ = "offer_performance"

    id: Mapped[uuid.UUID] = _uuid_col()
    offer_name: Mapped[str] = mapped_column(sa.String(), nullable=False)
    eligibility_rate: Mapped[Decimal] = mapped_column(sa.Numeric(6, 4), nullable=False)
    activation_rate: Mapped[Decimal] = mapped_column(sa.Numeric(6, 4), nullable=False)
    fulfillment_rate: Mapped[Decimal] = mapped_column(sa.Numeric(6, 4), nullable=False)
    day_30_impact: Mapped[Decimal] = mapped_column(sa.Numeric(6, 4), nullable=False)
    day_90_impact: Mapped[Decimal] = mapped_column(sa.Numeric(6, 4), nullable=False)
    period: Mapped[str] = mapped_column(sa.String(), nullable=False)
    created_at: Mapped[datetime] = _ts_col()
    updated_at: Mapped[datetime] = _ts_col()
