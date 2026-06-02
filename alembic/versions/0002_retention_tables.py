"""Add 6 retention tables.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pfi_milestones — optional FK → cohorts
    op.create_table(
        "pfi_milestones",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("cohort_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("milestone_type", sa.String(), nullable=False),
        sa.Column("target_pct", sa.Numeric(6, 4), nullable=False),
        sa.Column("actual_pct", sa.Numeric(6, 4), nullable=False),
        sa.Column("target_days", sa.Integer(), nullable=False),
        sa.Column("switching_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_pfi_milestones"),
        sa.ForeignKeyConstraint(
            ["cohort_id"], ["cohorts.id"],
            name="fk_pfi_milestones_cohort_id",
        ),
    )

    # cohort_retention_heatmap — optional FK → cohorts
    op.create_table(
        "cohort_retention_heatmap",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("cohort_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("acquisition_month", sa.String(), nullable=False),
        sa.Column("mob", sa.Integer(), nullable=False),
        sa.Column("retention_rate", sa.Numeric(6, 4), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("quality_score_band", sa.String(), nullable=False),
        sa.Column("market", sa.String(), nullable=False),
        sa.Column("offer_type", sa.String(), nullable=False),
        sa.Column("product_mix", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_cohort_retention_heatmap"),
        sa.ForeignKeyConstraint(
            ["cohort_id"], ["cohorts.id"],
            name="fk_cohort_retention_heatmap_cohort_id",
        ),
    )

    # bei_scores
    op.create_table(
        "bei_scores",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("market_tier", sa.String(), nullable=False),
        sa.Column("period", sa.String(), nullable=False),
        sa.Column("ease_of_banking", sa.Numeric(6, 4), nullable=False),
        sa.Column("trust", sa.Numeric(6, 4), nullable=False),
        sa.Column("value_perception", sa.Numeric(6, 4), nullable=False),
        sa.Column("digital_experience", sa.Numeric(6, 4), nullable=False),
        sa.Column("service_quality", sa.Numeric(6, 4), nullable=False),
        sa.Column("composite_score", sa.Numeric(6, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_bei_scores"),
    )

    # behavioral_triggers
    op.create_table(
        "behavioral_triggers",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("trigger_name", sa.String(), nullable=False),
        sa.Column("condition", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("volume_per_week", sa.Integer(), nullable=False),
        sa.Column("conversion_rate", sa.Numeric(6, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_behavioral_triggers"),
    )

    # geo_retention
    op.create_table(
        "geo_retention",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("geography", sa.String(), nullable=False),
        sa.Column("lat", sa.Numeric(9, 6), nullable=False),
        sa.Column("lon", sa.Numeric(9, 6), nullable=False),
        sa.Column("retention_90d", sa.Numeric(6, 4), nullable=False),
        sa.Column("market_tier", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_geo_retention"),
    )

    # offer_performance
    op.create_table(
        "offer_performance",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("offer_name", sa.String(), nullable=False),
        sa.Column("eligibility_rate", sa.Numeric(6, 4), nullable=False),
        sa.Column("activation_rate", sa.Numeric(6, 4), nullable=False),
        sa.Column("fulfillment_rate", sa.Numeric(6, 4), nullable=False),
        sa.Column("day_30_impact", sa.Numeric(6, 4), nullable=False),
        sa.Column("day_90_impact", sa.Numeric(6, 4), nullable=False),
        sa.Column("period", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_offer_performance"),
    )


def downgrade() -> None:
    op.drop_table("offer_performance")
    op.drop_table("geo_retention")
    op.drop_table("behavioral_triggers")
    op.drop_table("bei_scores")
    op.drop_table("cohort_retention_heatmap")
    op.drop_table("pfi_milestones")
