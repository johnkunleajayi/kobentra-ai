"""Add temporary Google OAuth transactions.

Revision ID: 2c002
Revises: 2c001
"""

from alembic import op
import sqlalchemy as sa


revision = "2c002"
down_revision = "2c001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "oauth_transactions",
        sa.Column(
            "id",
            sa.String(36),
            primary_key=True,
        ),
        sa.Column(
            "state_hash",
            sa.String(64),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "nonce",
            sa.String(128),
            nullable=False,
        ),
        sa.Column(
            "code_verifier",
            sa.String(128),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "consumed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_oauth_transactions_expires_at",
        "oauth_transactions",
        ["expires_at"],
    )


def downgrade():
    op.drop_index(
        "ix_oauth_transactions_expires_at",
        table_name="oauth_transactions",
    )

    op.drop_table("oauth_transactions")
