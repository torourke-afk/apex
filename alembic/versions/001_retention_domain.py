"""Retention domain — 6 tables for retention & onboarding analytics.

Revision ID: 001
Revises:
Create Date: 2026-05-08
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # pfi_milestones
    # ------------------------------------------------------------------
    op.create_table(
        "pfi_milestones",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "milestone_type",
            sa.Enum(
                "direct_deposit",
                "bill_pay",
                "debit_card",
                "digital_wallet",
                "p2p_payments",
                "cross_sell",
                name="milestonetype",
            ),
            nullable=False,
        ),
        sa.Column("target_pct", sa.Numeric(6, 4), nullable=False),
        sa.Column("actual_pct", sa.Numeric(6, 4), nullable=False),
        sa.Column("target_days", sa.Integer(), nullable=False),
        sa.Column("tracking_source", sa.String(), nullable=False),
        sa.Column(
            "switching_cost",
            sa.Enum("low", "medium", "high", name="switchingcost"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------
    # retention_cohorts
    # ------------------------------------------------------------------
    op.create_table(
        "retention_cohorts",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("acquisition_month", sa.String(7), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("market", sa.String(), nullable=False),
        sa.Column("offer_type", sa.String(), nullable=False),
        sa.Column("product_mix", sa.String(), nullable=False),
        sa.Column("quality_score_band", sa.String(), nullable=False),
        sa.Column("mob", sa.Integer(), nullable=False),
        sa.Column("retention_rate", sa.Numeric(6, 4), nullable=False),
        sa.Column("active_accounts", sa.Integer(), nullable=False),
        sa.Column("churned_accounts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------
    # bei_scores
    # ------------------------------------------------------------------
    op.create_table(
        "bei_scores",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("market_tier", sa.String(), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("direct_deposit_score", sa.Numeric(7, 2), nullable=False),
        sa.Column("digital_adoption_score", sa.Numeric(7, 2), nullable=False),
        sa.Column("cross_sell_score", sa.Numeric(7, 2), nullable=False),
        sa.Column("product_depth_score", sa.Numeric(7, 2), nullable=False),
        sa.Column("engagement_score", sa.Numeric(7, 2), nullable=False),
        sa.Column("composite_score", sa.Numeric(7, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("market_tier", "period", name="uq_bei_scores_tier_period"),
    )

    # ------------------------------------------------------------------
    # behavioral_triggers
    # ------------------------------------------------------------------
    op.create_table(
        "behavioral_triggers",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("trigger_name", sa.String(), nullable=False),
        sa.Column("condition", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("volume_per_week", sa.Integer(), nullable=False),
        sa.Column("conversion_rate", sa.Numeric(6, 4), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------
    # geo_retention
    # ------------------------------------------------------------------
    op.create_table(
        "geo_retention",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("geography", sa.String(), nullable=False),
        sa.Column("lat", sa.Numeric(9, 6), nullable=False),
        sa.Column("lon", sa.Numeric(9, 6), nullable=False),
        sa.Column("retention_90d", sa.Numeric(6, 4), nullable=False),
        sa.Column("market_tier", sa.String(), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("geography", "period", name="uq_geo_retention_geo_period"),
    )

    # ------------------------------------------------------------------
    # offer_performance
    # ------------------------------------------------------------------
    op.create_table(
        "offer_performance",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("offer_name", sa.String(), nullable=False),
        sa.Column("eligibility_rate", sa.Numeric(6, 4), nullable=False),
        sa.Column("activation_rate", sa.Numeric(6, 4), nullable=False),
        sa.Column("fulfillment_rate", sa.Numeric(6, 4), nullable=False),
        sa.Column("day_30_impact", sa.Numeric(18, 4), nullable=False),
        sa.Column("day_90_impact", sa.Numeric(18, 4), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("offer_name", "period", name="uq_offer_performance_name_period"),
    )


def downgrade() -> None:
    op.drop_table("offer_performance")
    op.drop_table("geo_retention")
    op.drop_table("behavioral_triggers")
    op.drop_table("bei_scores")
    op.drop_table("retention_cohorts")
    op.drop_table("pfi_milestones")
    # Drop enums (PostgreSQL only — DuckDB ignores)
    op.execute("DROP TYPE IF EXISTS milestonetype")
    op.execute("DROP TYPE IF EXISTS switchingcost")
