"""Durable business deletion operations and immutable transition events."""

import sqlalchemy as sa
from alembic import op

revision = "2l002"
down_revision = "2l001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "business_deletions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False, unique=True),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("state", sa.String(40), nullable=False),
        sa.Column("error_code", sa.String(60)),
        sa.Column("target", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "state IN ('local_pending','salesforce_pending','salesforce_retry','awaiting_permanent_purge','completed')",
            name="deletion_state",
        ),
    )
    op.create_table(
        "business_deletion_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "operation_id", sa.String(36), sa.ForeignKey("business_deletions.id"), nullable=False
        ),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("state", sa.String(40), nullable=False),
        sa.Column("error_code", sa.String(60)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("operation_id", "id", name="uq_deletion_event"),
    )
    op.create_index(
        "ix_business_deletion_events_operation_id", "business_deletion_events", ["operation_id"]
    )


def downgrade():
    op.drop_index("ix_business_deletion_events_operation_id", table_name="business_deletion_events")
    op.drop_table("business_deletion_events")
    op.drop_table("business_deletions")
