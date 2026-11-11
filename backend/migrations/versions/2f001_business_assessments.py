"""Track business assessment initiation without asserting provider completion."""

import sqlalchemy as sa
from alembic import op

revision = "2f001"
down_revision = "2c002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "business_assessments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False
        ),
        sa.Column(
            "business_id",
            sa.String(36),
            sa.ForeignKey("business_profiles.organization_id"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("assessment_type", sa.String(60), nullable=False),
        sa.Column("provider_survey_id", sa.String(100), nullable=False),
        sa.Column("provider_logical_id", sa.String(100), nullable=False),
        sa.Column("provider_response_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("initiated_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("initiated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synchronized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("integration_mode", sa.String(40), nullable=False),
        sa.CheckConstraint("business_id = organization_id", name="assessment_business_tenant"),
        sa.CheckConstraint("provider = 'surveyvista'", name="assessment_provider"),
        sa.CheckConstraint(
            "integration_mode = 'shared_public_link'", name="assessment_integration_mode"
        ),
        sa.CheckConstraint(
            "status IN ('initiated','launch_requested','completed_verified')",
            name="assessment_status",
        ),
        sa.CheckConstraint(
            "(status IN ('initiated','launch_requested') AND provider_response_id IS NULL "
            "AND completed_at IS NULL AND synchronized_at IS NULL) OR "
            "(status = 'completed_verified' AND provider_response_id IS NOT NULL "
            "AND completed_at IS NOT NULL AND synchronized_at IS NOT NULL)",
            name="assessment_completion_evidence",
        ),
        sa.UniqueConstraint(
            "provider", "provider_response_id", name="uq_assessment_provider_response"
        ),
    )
    op.create_index(
        "ix_business_assessments_organization_id", "business_assessments", ["organization_id"]
    )


def downgrade():
    op.drop_index("ix_business_assessments_organization_id", table_name="business_assessments")
    op.drop_table("business_assessments")

