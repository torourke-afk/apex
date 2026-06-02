"""Initial schema — all 8 Apex tables.

Revision ID: 0001
Revises:
Create Date: 2026-05-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # campaigns — no FKs, must exist before funnel_events
    op.create_table(
        "campaigns",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("spend", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("revenue", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_campaigns"),
    )

    # funnel_events — FK → campaigns
    op.create_table(
        "funnel_events",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("campaign_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("stage", sa.String(), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("value", sa.Numeric(18, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_funnel_events"),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["campaigns.id"],
            name="fk_funnel_events_campaign_id",
        ),
    )

    # cohorts
    op.create_table(
        "cohorts",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("segment", sa.String(), nullable=False),
        sa.Column("criteria", sa.JSON(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_cohorts"),
    )

    # offers
    op.create_table(
        "offers",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("product", sa.String(), nullable=False),
        sa.Column("offer_type", sa.String(), nullable=False),
        sa.Column("value", sa.Numeric(18, 4), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_offers"),
    )

    # alerts
    op.create_table(
        "alerts",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False, server_default="info"),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_alerts"),
    )

    # budgets
    op.create_table(
        "budgets",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("period", sa.String(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("allocated", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("actual", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_budgets"),
    )

    # scenarios
    op.create_table(
        "scenarios",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("base_budget", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("results", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_scenarios"),
    )

    # directives
    op.create_table(
        "directives",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("directive_type", sa.String(), nullable=False),
        sa.Column("priority", sa.String(), nullable=False, server_default="medium"),
        sa.Column("owner", sa.String(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_directives"),
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("directives")
    op.drop_table("scenarios")
    op.drop_table("budgets")
    op.drop_table("alerts")
    op.drop_table("offers")
    op.drop_table("cohorts")
    op.drop_table("funnel_events")
    op.drop_table("campaigns")
