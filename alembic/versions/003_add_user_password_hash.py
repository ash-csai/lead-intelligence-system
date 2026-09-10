"""Add password_hash column to the users table.

Revision ID: 003_add_user_password_hash
Revises: 002_add_tenant_aware_organizations
Create Date: 2026-09-10
"""

from alembic import op
import sqlalchemy as sa


revision = "003_add_user_password_hash"
down_revision = "002_add_tenant_aware_organizations"
branch_labels = None
depends_on = None


def upgrade():
    """Backfill the nullable password_hash column for the users table."""
    bind = op.get_bind()
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("password_hash", sa.String(length=255), nullable=True))


def downgrade():
    """Drop the password_hash column from the users table."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("password_hash")
