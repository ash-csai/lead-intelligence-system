"""Initial migration - baseline schema from database/schema.sql

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-08-30

This is the baseline migration representing the current database schema.
All existing databases will be marked as having this migration already applied.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the baseline schema."""
    # Institutions table
    op.create_table(
        "institutions",
        sa.Column("institution_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("contact_person", sa.String(), nullable=True),
        sa.Column("contact_phone", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("institution_id"),
        sa.CheckConstraint("type IN ('school','coaching_center')"),
    )

    # Leads table
    op.create_table(
        "leads",
        sa.Column("lead_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_name", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True, unique=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("school_id", sa.Integer(), nullable=True),
        sa.Column("coaching_id", sa.Integer(), nullable=True),
        sa.Column("course_interest", sa.String(), nullable=True),
        sa.Column("lead_source", sa.String(), nullable=True),
        sa.Column("interest_level", sa.String(), nullable=True),
        sa.Column("lead_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(), nullable=False, server_default="new"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("notes", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("lead_id"),
        sa.UniqueConstraint("phone", name="uq_phone"),
        sa.ForeignKeyConstraint(["school_id"], ["institutions.institution_id"]),
        sa.ForeignKeyConstraint(["coaching_id"], ["institutions.institution_id"]),
        sa.CheckConstraint("interest_level IN ('high','medium','low')"),
        sa.CheckConstraint("status IN ('new','contacted','interested','applied','admitted','lost')"),
    )

    # Interactions table
    op.create_table(
        "interactions",
        sa.Column("interaction_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("interaction_type", sa.String(), nullable=False),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("follow_up_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("interaction_id"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.lead_id"]),
        sa.CheckConstraint("interaction_type IN ('call','visit','application','whatsapp','email')"),
    )

    # Users table
    op.create_table(
        "users",
        sa.Column("user_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("role", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    """Remove all tables (only for testing/development)."""
    op.drop_table("users")
    op.drop_table("interactions")
    op.drop_table("leads")
    op.drop_table("institutions")
