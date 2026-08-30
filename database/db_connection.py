"""Database connection and configuration using SQLAlchemy."""

import os
from flask_sqlalchemy import SQLAlchemy
from database.models import db

DB_NAME = os.environ.get("DATABASE_URL", "sqlite:///lead_system.db")


def configure_db(app):
    """Configure SQLAlchemy for the Flask app."""
    app.config["SQLALCHEMY_DATABASE_URI"] = DB_NAME
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)


def get_db():
    """Get the SQLAlchemy db instance (for compatibility with existing code)."""
    return db


def close_db(e=None):
    """Close database session on app context teardown."""
    # SQLAlchemy handles this automatically via Flask integration
    pass


def init_db(app):
    """Initialize database tables."""
    with app.app_context():
        db.create_all()

