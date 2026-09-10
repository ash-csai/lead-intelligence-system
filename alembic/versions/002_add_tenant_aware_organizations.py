"""Add organizations table and organization_id foreign keys.

Revision ID: 002_add_tenant_aware_organizations
Revises: 001_initial_schema
Create Date: 2026-09-10

This migration creates the single default organization and backfills every
existing row in the legacy single-tenant database. It is intentionally schema-only
and does not add any query filtering by organization.
"""

from alembic import op
import sqlalchemy as sa


revision = "002_add_tenant_aware_organizations"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade():
    """Create organizations and rebuild every schema table so organization_id is attached safely without losing original CHECK constraints."""
    bind = op.get_bind()

    # Create organizations table.
    op.create_table(
        "organizations",
        sa.Column("organization_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("organization_id"),
    )

    # Seed a default organization.
    bind.execute(sa.text("INSERT INTO organizations (name) VALUES ('Default Organization')"))
    default_org_id = bind.execute(
        sa.text("SELECT organization_id FROM organizations WHERE name = 'Default Organization' LIMIT 1")
    ).scalar()

    # Rename the original tables out of the way.
    op.rename_table("institutions", "institutions_old")
    op.rename_table("leads", "leads_old")
    op.rename_table("interactions", "interactions_old")
    op.rename_table("users", "users_old")

    # Rebuild institutions.
    bind.execute(sa.text("""
        CREATE TABLE institutions (
            institution_id INTEGER NOT NULL,
            name VARCHAR NOT NULL,
            type VARCHAR,
            city VARCHAR,
            contact_person VARCHAR,
            contact_phone VARCHAR,
            notes VARCHAR,
            created_at DATETIME NOT NULL,
            organization_id INTEGER NOT NULL,
            PRIMARY KEY (institution_id),
            CONSTRAINT fk_institutions_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id),
            CHECK (type IN ('school','coaching_center'))
        )
    """))
    bind.execute(sa.text("""
        INSERT INTO institutions (institution_id, name, type, city, contact_person, contact_phone, notes, created_at, organization_id)
        SELECT institution_id, name, type, city, contact_person, contact_phone, notes, created_at, :org_id
        FROM institutions_old
    """), {"org_id": default_org_id})

    # Rebuild leads.
    bind.execute(sa.text("""
        CREATE TABLE leads (
            lead_id INTEGER NOT NULL,
            student_name VARCHAR NOT NULL,
            phone VARCHAR,
            city VARCHAR,
            school_id INTEGER,
            coaching_id INTEGER,
            course_interest VARCHAR,
            lead_source VARCHAR,
            interest_level VARCHAR,
            lead_score INTEGER DEFAULT '0' NOT NULL,
            status VARCHAR DEFAULT 'new' NOT NULL,
            created_at DATETIME NOT NULL,
            notes VARCHAR,
            organization_id INTEGER NOT NULL,
            PRIMARY KEY (lead_id),
            CONSTRAINT uq_phone UNIQUE (phone),
            CONSTRAINT fk_leads_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id),
            FOREIGN KEY(school_id) REFERENCES institutions (institution_id),
            FOREIGN KEY(coaching_id) REFERENCES institutions (institution_id),
            CHECK (interest_level IN ('high','medium','low')),
            CHECK (status IN ('new','contacted','interested','applied','admitted','lost')),
            UNIQUE (phone)
        )
    """))
    bind.execute(sa.text("""
        INSERT INTO leads (
            lead_id, student_name, phone, city, school_id, coaching_id,
            course_interest, lead_source, interest_level, lead_score,
            status, created_at, notes, organization_id
        )
        SELECT
            lead_id, student_name, phone, city, school_id, coaching_id,
            course_interest, lead_source, interest_level, lead_score,
            status, created_at, notes, :org_id
        FROM leads_old
    """), {"org_id": default_org_id})

    # Rebuild interactions.
    bind.execute(sa.text("""
        CREATE TABLE interactions (
            interaction_id INTEGER NOT NULL,
            lead_id INTEGER NOT NULL,
            interaction_type VARCHAR NOT NULL,
            notes VARCHAR,
            follow_up_date DATE,
            created_at DATETIME NOT NULL,
            organization_id INTEGER NOT NULL,
            PRIMARY KEY (interaction_id),
            CONSTRAINT fk_interactions_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id),
            FOREIGN KEY(lead_id) REFERENCES leads (lead_id),
            CHECK (interaction_type IN ('call','visit','application','whatsapp','email'))
        )
    """))
    bind.execute(sa.text("""
        INSERT INTO interactions (interaction_id, lead_id, interaction_type, notes, follow_up_date, created_at, organization_id)
        SELECT interaction_id, lead_id, interaction_type, notes, follow_up_date, created_at, :org_id
        FROM interactions_old
    """), {"org_id": default_org_id})

    # Rebuild users.
    bind.execute(sa.text("""
        CREATE TABLE users (
            user_id INTEGER NOT NULL,
            name VARCHAR,
            email VARCHAR,
            role VARCHAR,
            created_at DATETIME NOT NULL,
            organization_id INTEGER NOT NULL,
            PRIMARY KEY (user_id),
            CONSTRAINT fk_users_organization FOREIGN KEY(organization_id) REFERENCES organizations (organization_id)
        )
    """))
    bind.execute(sa.text("""
        INSERT INTO users (user_id, name, email, role, created_at, organization_id)
        SELECT user_id, name, email, role, created_at, :org_id
        FROM users_old
    """), {"org_id": default_org_id})

    # Drop stale renamed tables.
    op.drop_table("institutions_old")
    op.drop_table("leads_old")
    op.drop_table("interactions_old")
    op.drop_table("users_old")


def downgrade():
    """Rollback this milestone by dropping the new tenant-aware tables."""
    op.drop_table("users")
    op.drop_table("interactions")
    op.drop_table("leads")
    op.drop_table("institutions")
    op.drop_table("organizations")
