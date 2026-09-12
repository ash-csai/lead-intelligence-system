"""Add an is_active boolean column to users.

Revision ID: 005_add_user_is_active
Revises: 004_add_roles_and_assigned_to
Create Date: 2026-09-13
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "005_add_user_is_active"
down_revision = "004_add_roles_and_assigned_to"
branch_labels = None
depends_on = None


def upgrade():
    """Add the persisted is_active flag for user login gating."""
    bind = op.get_bind()
    try:
        op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    except Exception:
        # SQLite and some older installs can need the table rebuilt through an explicit column copy.
        bind.execute(sa.text("ALTER TABLE users RENAME TO users_old"))
        bind.execute(sa.text("""
            CREATE TABLE users (
                user_id INTEGER NOT NULL PRIMARY KEY,
                name VARCHAR,
                email VARCHAR,
                role VARCHAR,
                password_hash VARCHAR(255),
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at TIMESTAMP NOT NULL,
                organization_id INTEGER NOT NULL,
                CONSTRAINT fk_users_organization FOREIGN KEY(organization_id) REFERENCES organizations(organization_id)
            )
        """))
        bind.execute(sa.text("""
            INSERT INTO users (user_id, name, email, role, password_hash, is_active, created_at, organization_id)
            SELECT user_id, name, email, role, password_hash, 1, created_at, organization_id
            FROM users_old
        """))
        bind.execute(sa.text("DROP TABLE users_old"))


def downgrade():
    """Drop the persisted user activation flag."""
    op.drop_column("users", "is_active")
