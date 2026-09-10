"""Database connection and configuration using SQLAlchemy."""

import sqlite3
from sqlalchemy import event
from sqlalchemy.engine import Engine
from database.models import db


def configure_db(app):
    """Configure SQLAlchemy for the Flask app and register SQLite FK enforcement.

    Values come from the Flask config object instead of a repository-level
    hardcoded `DB_NAME` variable, keeping the database URI centralized and
    deterministic for test, development, and production environments.
    """
    uri = app.config.get("SQLALCHEMY_DATABASE_URI")
    if not uri:
        from config import Config
        uri = Config.SQLALCHEMY_DATABASE_URI

    app.config["SQLALCHEMY_DATABASE_URI"] = uri
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    db.init_app(app)

    @event.listens_for(Engine, "connect")
    def enable_sqlite_fk(dbapi_connection, connection_record):
        if isinstance(dbapi_connection, sqlite3.Connection):
            dbapi_connection.execute("PRAGMA foreign_keys=ON")


def get_db():
    """Return the Flask-SQLAlchemy extension for the ORM session-backed compatibility layer."""
    return db


def close_db(e=None):
    """Close database session on app context teardown."""
    # SQLAlchemy handles this automatically via Flask integration
    pass

