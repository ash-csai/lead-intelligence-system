"""Add a per-user hashed API bearer token table.

Revision ID: 006_add_api_token
Revises: 005_add_user_is_active
Create Date: 2026-09-13
"""

from alembic import op
import sqlalchemy as sa


revision = "006_add_api_token"
down_revision = "005_add_user_is_active"
branch_labels = None
depends_on = None


def upgrade():
    """Create the api_tokens table for bearer-token storage and authentication."""
    op.create_table(
        "api_tokens",
        sa.Column("token_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("token_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.UniqueConstraint("user_id", name="uq_api_tokens_user_id"),
        sa.UniqueConstraint("token_hash", name="uq_api_tokens_token_hash"),
    )


def downgrade():
    """Drop the api_tokens table."""
    op.drop_table("api_tokens")
