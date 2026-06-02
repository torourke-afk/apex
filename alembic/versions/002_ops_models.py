"""Ops Command Center domain — 5 tables for operational data entities.

Revision ID: 002
Revises: 001
Create Date: 2026-05-08
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # calendar_events
    # ------------------------------------------------------------------
    op.create_table(
        "calendar_events",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "event_type",
            sa.Enum(
                "campaign_launch",
                "review_cycle",
                "compliance_deadline",
                "exec_briefing",
                "budget_review",
                "team_sync",
                "other",
                name="eventtype",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "scheduled",
                "in_progress",
                "completed",
                "cancelled",
                name="eventstatus",
            ),
            nullable=False,
            server_default="scheduled",
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("start_dt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_dt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner", sa.String(), nullable=False),
        sa.Column("attendees", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("related_campaign_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------
    # approval_items
    # ------------------------------------------------------------------
    op.create_table(
        "approval_items",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "category",
            sa.Enum(
                "creative",
                "budget_change",
                "compliance",
                "vendor_contract",
                "campaign_brief",
                "other",
                name="approvalcategory",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "in_review",
                "approved",
                "rejected",
                "escalated",
                name="approvalstatus",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "priority",
            sa.Enum("low", "medium", "high", "urgent", name="approvalpriority"),
            nullable=False,
            server_default="medium",
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("requestor", sa.String(), nullable=False),
        sa.Column("approver", sa.String(), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("budget_impact", sa.Numeric(18, 4), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("artifact_url", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------
    # system_health_checks
    # ------------------------------------------------------------------
    op.create_table(
        "system_health_checks",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "category",
            sa.Enum(
                "data_pipeline",
                "api_integration",
                "platform_connection",
                "database",
                "reporting",
                "other",
                name="systemcategory",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "healthy",
                "degraded",
                "down",
                "maintenance",
                "unknown",
                name="systemstatus",
            ),
            nullable=False,
        ),
        sa.Column("system_name", sa.String(255), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("uptime_pct", sa.Numeric(7, 4), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("owner_team", sa.String(), nullable=True),
        sa.Column("last_incident_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------
    # competitive_intel_items
    # ------------------------------------------------------------------
    op.create_table(
        "competitive_intel_items",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "category",
            sa.Enum(
                "rate_change",
                "product_launch",
                "marketing_campaign",
                "branch_expansion",
                "partnership",
                "regulatory",
                "other",
                name="intelcategory",
            ),
            nullable=False,
        ),
        sa.Column(
            "impact",
            sa.Enum("low", "medium", "high", "critical", name="intelimpact"),
            nullable=False,
            server_default="medium",
        ),
        sa.Column("competitor_name", sa.String(), nullable=False),
        sa.Column("headline", sa.String(500), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("observed_date", sa.Date(), nullable=False),
        sa.Column("product_affected", sa.String(), nullable=True),
        sa.Column("rate_delta_bps", sa.Integer(), nullable=True),
        sa.Column("response_recommended", sa.Text(), nullable=True),
        sa.Column("is_actioned", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------
    # team_capacity
    # ------------------------------------------------------------------
    op.create_table(
        "team_capacity",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "function",
            sa.Enum(
                "brand",
                "performance_media",
                "seo_content",
                "analytics",
                "creative",
                "product_marketing",
                "ops",
                "other",
                name="teamfunction",
            ),
            nullable=False,
        ),
        sa.Column("team_name", sa.String(), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("headcount_total", sa.Integer(), nullable=False),
        sa.Column("headcount_fte", sa.Integer(), nullable=False),
        sa.Column("open_reqs", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("utilization_pct", sa.Numeric(6, 2), nullable=False),
        sa.Column("capacity_available_hrs", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_name", "period", name="uq_team_capacity_name_period"),
    )


def downgrade() -> None:
    op.drop_table("team_capacity")
    op.drop_table("competitive_intel_items")
    op.drop_table("system_health_checks")
    op.drop_table("approval_items")
    op.drop_table("calendar_events")
    # Drop enums (PostgreSQL only — DuckDB ignores)
    op.execute("DROP TYPE IF EXISTS teamfunction")
    op.execute("DROP TYPE IF EXISTS intelimpact")
    op.execute("DROP TYPE IF EXISTS intelcategory")
    op.execute("DROP TYPE IF EXISTS systemstatus")
    op.execute("DROP TYPE IF EXISTS systemcategory")
    op.execute("DROP TYPE IF EXISTS approvalpriority")
    op.execute("DROP TYPE IF EXISTS approvalstatus")
    op.execute("DROP TYPE IF EXISTS approvalcategory")
    op.execute("DROP TYPE IF EXISTS eventstatus")
    op.execute("DROP TYPE IF EXISTS eventtype")
