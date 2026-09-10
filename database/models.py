"""SQLAlchemy ORM models mirroring the database schema."""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint

db = SQLAlchemy()


class Institution(db.Model):
    """Institutions table — schools and coaching centers."""

    __tablename__ = "institutions"
    __table_args__ = (
        CheckConstraint("type IN ('school','coaching_center')"),
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


class User(db.Model):
    """Users table — for future expansion."""

    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=True)
    email = db.Column(db.String, nullable=True)
    role = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<User {self.user_id}: {self.name}>"
