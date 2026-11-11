"""Immutable tenant-scoped self-reported qualification evidence."""

from importlib import import_module

import sqlalchemy as sa
from alembic import context, op

revision = "2h001"
down_revision = "2g001"
branch_labels = None
depends_on = None


def batch_options(with_constraint=False):
    if context.is_offline_mode() and op.get_context().dialect.name == "sqlite":
        table = import_module("migrations.versions.2g001_native_surveyvista").snapshot(native=True)
        if with_constraint:
            table.append_constraint(
                sa.UniqueConstraint("id", "organization_id", name="uq_assessment_id_org")
            )
        return {"copy_from": table}
    return {}


def upgrade():
    with op.batch_alter_table("business_assessments", **batch_options()) as batch:
        batch.create_unique_constraint("uq_assessment_id_org", ["id", "organization_id"])
    op.create_table(
        "assessment_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False
        ),
        sa.Column("assessment_id", sa.String(36), nullable=False),
        sa.Column("provider_response_id", sa.String(18), nullable=False),
        sa.Column("extraction_version", sa.String(40), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("evidence_kind", sa.String(30), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("gaps", sa.JSON(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["assessment_id", "organization_id"],
            ["business_assessments.id", "business_assessments.organization_id"],
        ),
        sa.UniqueConstraint(
            "assessment_id", "extraction_version", name="uq_assessment_evidence_version"
        ),
        sa.CheckConstraint("evidence_kind = 'self_reported'", name="assessment_evidence_kind"),
    )
    op.create_index(
        "ix_assessment_evidence_organization_id", "assessment_evidence", ["organization_id"]
    )


def downgrade():
    # Explicit downgrade is destructive to this evidence table; never run remotely
    # without review. No deployed 2G data is changed by the upgrade.
    op.drop_index("ix_assessment_evidence_organization_id", table_name="assessment_evidence")
    op.drop_table("assessment_evidence")
    with op.batch_alter_table(
        "business_assessments", **batch_options(with_constraint=True)
    ) as batch:
        batch.drop_constraint("uq_assessment_id_org", type_="unique")
