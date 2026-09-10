"""Database connection and configuration using SQLAlchemy."""

import os
import sqlite3
from sqlalchemy import event
from sqlalchemy.engine import Engine
from database.models import db

db_url = os.environ.get("DATABASE_URL")
if not db_url:
    # Resolve absolute path to lead_system.db in workspace root
    db_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(db_dir, "lead_system.db").replace("\\", "/")
    db_url = f"sqlite:///{db_path}"

DB_NAME = db_url


def configure_db(app):
    """Configure SQLAlchemy for the Flask app and register SQLite FK enforcement."""
    app.config["SQLALCHEMY_DATABASE_URI"] = DB_NAME
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
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

