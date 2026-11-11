"""Independent business administrative states and append-only decision history."""

import sqlalchemy as sa
from alembic import op

revision = "2l001"
down_revision = "2h001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "business_administration",
        sa.Column(
            "organization_id", sa.String(36), sa.ForeignKey("organizations.id"), primary_key=True
        ),
        sa.Column("approval", sa.String(12), nullable=False, server_default="pending"),
        sa.Column("identity", sa.String(12), nullable=False, server_default="unverified"),
        sa.Column("access", sa.String(12), nullable=False, server_default="active"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint("approval IN ('pending','approved','rejected')", name="admin_approval"),
        sa.CheckConstraint("identity IN ('unverified','verified')", name="admin_identity"),
        sa.CheckConstraint("access IN ('active','suspended')", name="admin_access"),
        sa.CheckConstraint("version >= 0", name="admin_version"),
    )
    op.create_table(
        "administrative_decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False
        ),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence_references", sa.JSON(), nullable=False),
        sa.Column("previous_values", sa.JSON(), nullable=False),
        sa.Column("new_values", sa.JSON(), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "request_id", name="uq_admin_request"),
    )
    op.create_index(
        "ix_administrative_decisions_organization_id",
        "administrative_decisions",
        ["organization_id"],
    )


def downgrade():
    op.drop_index(
        "ix_administrative_decisions_organization_id", table_name="administrative_decisions"
    )
    op.drop_table("administrative_decisions")
    op.drop_table("business_administration")
