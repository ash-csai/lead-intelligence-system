"""SQLAlchemy ORM models mirroring the database schema."""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class Organization(db.Model):
    """Organizations (tenants) table."""

    __tablename__ = "organizations"

    organization_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)


class Institution(db.Model):
    """Institutions table — schools and coaching centers."""

    __tablename__ = "institutions"
    __table_args__ = (
        CheckConstraint("type IN ('school','coaching_center')"),
    )

    organization_id = db.Column(
        db.Integer,
        db.ForeignKey("organizations.organization_id"),
        nullable=False,
        default=1,
    )
    institution_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    type = db.Column(
        db.String,
        nullable=True,
    )
    city = db.Column(db.String, nullable=True)
    contact_person = db.Column(db.String, nullable=True)
    contact_phone = db.Column(db.String, nullable=True)
    notes = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    leads_as_school = db.relationship(
        "Lead",
        foreign_keys="Lead.school_id",
        backref="school",
        cascade="all, delete-orphan",
    )
    leads_as_coaching = db.relationship(
        "Lead",
        foreign_keys="Lead.coaching_id",
        backref="coaching",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Institution {self.institution_id}: {self.name}>"


class Lead(db.Model):
    """Leads table — student/prospect records."""

    __tablename__ = "leads"
    __table_args__ = (
        CheckConstraint("interest_level IN ('high','medium','low')"),
        CheckConstraint("status IN ('new','contacted','interested','applied','admitted','lost')"),
    )

    organization_id = db.Column(
        db.Integer,
        db.ForeignKey("organizations.organization_id"),
        nullable=False,
        default=1,
    )
    lead_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_name = db.Column(db.String, nullable=False)
    phone = db.Column(db.String, unique=True, nullable=True)
    city = db.Column(db.String, nullable=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("institutions.institution_id"),
        nullable=True,
    )
    coaching_id = db.Column(
        db.Integer,
        db.ForeignKey("institutions.institution_id"),
        nullable=True,
    )
    course_interest = db.Column(db.String, nullable=True)
    lead_source = db.Column(db.String, nullable=True)
    interest_level = db.Column(
        db.String,
        nullable=True,
    )
    lead_score = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(
        db.String,
        default="new",
        nullable=False,
    )
    assigned_to = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id"),
        nullable=True,
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    notes = db.Column(db.String, nullable=True)

    # Relationships
    interactions = db.relationship(
        "Interaction",
        backref="lead",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    def __repr__(self):
        return f"<Lead {self.lead_id}: {self.student_name}>"


class Interaction(db.Model):
    """Interactions table — calls, visits, applications, etc."""

    __tablename__ = "interactions"
    __table_args__ = (
        CheckConstraint("interaction_type IN ('call','visit','application','whatsapp','email')"),
    )

    organization_id = db.Column(
        db.Integer,
        db.ForeignKey("organizations.organization_id"),
        nullable=False,
        default=1,
    )
    interaction_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    lead_id = db.Column(
        db.Integer,
        db.ForeignKey("leads.lead_id"),
        nullable=False,
    )
    interaction_type = db.Column(
        db.String,
        nullable=False,
    )
    notes = db.Column(db.String, nullable=True)
    follow_up_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Interaction {self.interaction_id}: {self.interaction_type}>"


class ApiToken(db.Model):
    """Hashed API bearer tokens issued to a specific user for the v1 API.

    A plaintext token is returned once to the caller and then discarded.
    Only the SHA-256 digest is stored in the database.
    """

    __tablename__ = "api_tokens"

    token_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False, unique=True)
    token_hash = db.Column(db.String(255), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", backref="api_token")


class User(UserMixin, db.Model):
    """Users table — logged-in account records with a role enum."""

    __tablename__ = "users"

    organization_id = db.Column(
        db.Integer,
        db.ForeignKey("organizations.organization_id"),
        nullable=False,
        default=1,
    )
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=True)
    email = db.Column(db.String, nullable=True)
    role = db.Column(db.String(32), nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def get_id(self):
        return str(self.user_id)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.user_id}: {self.name}>"
