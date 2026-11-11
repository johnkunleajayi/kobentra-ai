"""Preserve legacy assessments; add durable native Salesforce dispatch state."""

import sqlalchemy as sa
from alembic import context, op

revision = "2g001"
down_revision = "2f001"
branch_labels = None
depends_on = None


def snapshot(native=False):
    """Frozen 2f schema for SQLite --sql batch rendering; no runtime model imports."""
    meta = sa.MetaData()
    sa.Table("organizations", meta, sa.Column("id", sa.String(36), primary_key=True))
    sa.Table("users", meta, sa.Column("id", sa.String(36), primary_key=True))
    sa.Table("business_profiles", meta, sa.Column("organization_id", sa.String(36), unique=True))
    table = sa.Table(
        "business_assessments",
        meta,
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
        sa.Column("initiated_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
    )
    for name, size, nullable in [
        ("provider", 30, False),
        ("assessment_type", 60, False),
        ("provider_survey_id", 100, False),
        ("provider_logical_id", 100, False),
        ("provider_response_id", 100, True),
        ("status", 30, False),
        ("integration_mode", 40, False),
    ]:
        table.append_column(sa.Column(name, sa.String(size), nullable=nullable))
    for name in ["initiated_at", "completed_at", "synchronized_at"]:
        table.append_column(
            sa.Column(name, sa.DateTime(timezone=True), nullable=name != "initiated_at")
        )
    for name, expression in {
        "assessment_business_tenant": "business_id = organization_id",
        "assessment_provider": "provider = 'surveyvista'",
        "assessment_status": "status IN ('initiated','launch_requested','completed_verified')",
        "assessment_completion_evidence": "(status IN ('initiated','launch_requested') AND provider_response_id IS NULL AND completed_at IS NULL AND synchronized_at IS NULL) OR (status = 'completed_verified' AND provider_response_id IS NOT NULL AND completed_at IS NOT NULL AND synchronized_at IS NOT NULL)",
        "assessment_integration_mode": "integration_mode IN ('shared_public_link','salesforce_flow')"
        if native
        else "integration_mode = 'shared_public_link'",
    }.items():
        table.append_constraint(sa.CheckConstraint(expression, name=name))
    table.append_constraint(
        sa.UniqueConstraint(
            "provider", "provider_response_id", name="uq_assessment_provider_response"
        )
    )
    sa.Index("ix_business_assessments_organization_id", table.c.organization_id)
    if native:
        for name, type_ in [
            ("salesforce_lead_id", sa.String(18)),
            ("correlation_id", sa.String(36)),
            ("dispatch_state", sa.String(20)),
            ("dispatch_started_at", sa.DateTime(timezone=True)),
            ("dispatch_payload", sa.JSON()),
        ]:
            table.append_column(sa.Column(name, type_, nullable=True))
        table.append_constraint(
            sa.UniqueConstraint("salesforce_lead_id", name="uq_assessment_lead")
        )
        table.append_constraint(
            sa.UniqueConstraint("correlation_id", name="uq_assessment_correlation")
        )
        table.append_constraint(
            sa.CheckConstraint(
                "dispatch_state IS NULL OR dispatch_state IN ('sending','uncertain','sent')",
                name="assessment_dispatch_state",
            )
        )
    return table


def batch_options(native=False):
    return (
        {"copy_from": snapshot(native)}
        if context.is_offline_mode() and op.get_context().dialect.name == "sqlite"
        else {}
    )


def upgrade():
    with op.batch_alter_table("business_assessments", **batch_options()) as batch:
        batch.drop_constraint("assessment_integration_mode", type_="check")
        batch.add_column(sa.Column("salesforce_lead_id", sa.String(18), nullable=True))
        batch.add_column(sa.Column("correlation_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("dispatch_state", sa.String(20), nullable=True))
        batch.add_column(
            sa.Column("dispatch_started_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(sa.Column("dispatch_payload", sa.JSON(), nullable=True))
        batch.create_unique_constraint("uq_assessment_lead", ["salesforce_lead_id"])
        batch.create_unique_constraint("uq_assessment_correlation", ["correlation_id"])
        batch.create_check_constraint(
            "assessment_dispatch_state",
            "dispatch_state IS NULL OR dispatch_state IN ('sending','uncertain','sent')",
        )
        batch.create_check_constraint(
            "assessment_integration_mode",
            "integration_mode IN ('shared_public_link','salesforce_flow')",
        )


def downgrade():
    # Never silently discard native Lead associations by downgrading populated data.
    connection = op.get_bind()
    if context.is_offline_mode():
        op.execute(
            "CREATE TEMPORARY TABLE kobentra_native_downgrade_guard (native_rows INTEGER CHECK (native_rows = 0))"
        )
        op.execute(
            "INSERT INTO kobentra_native_downgrade_guard SELECT COUNT(*) FROM business_assessments WHERE integration_mode = 'salesforce_flow' OR dispatch_state IS NOT NULL"
        )
        op.execute("DROP TABLE kobentra_native_downgrade_guard")
    elif connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM business_assessments WHERE integration_mode = 'salesforce_flow' OR dispatch_state IS NOT NULL"
        )
    ).scalar():
        raise RuntimeError("Native assessment data must be reviewed before downgrade")
    with op.batch_alter_table("business_assessments", **batch_options(native=True)) as batch:
        batch.drop_constraint("assessment_integration_mode", type_="check")
        batch.drop_constraint("assessment_dispatch_state", type_="check")
        batch.drop_constraint("uq_assessment_lead", type_="unique")
        batch.drop_constraint("uq_assessment_correlation", type_="unique")
        for column in [
            "salesforce_lead_id",
            "correlation_id",
            "dispatch_state",
            "dispatch_started_at",
            "dispatch_payload",
        ]:
            batch.drop_column(column)
        batch.create_check_constraint(
            "assessment_integration_mode", "integration_mode = 'shared_public_link'"
        )
