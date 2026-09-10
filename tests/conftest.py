"""Pytest configuration and fixtures for Lead Intelligence System tests."""

import os
import tempfile
from pathlib import Path

import pytest
from app import create_app


@pytest.fixture
def temp_db(app):
    """Provide a SQLAlchemy database object (with sessions) inside application context."""
    from database.db_connection import get_db
    with app.app_context():
        yield get_db()


@pytest.fixture
def app(tmp_path, monkeypatch):
    """Create Flask app with temporary database for testing."""
    # Create temporary database
    db_path = tmp_path / "test.db"
    db_path_str = str(db_path)
    db_url = f"sqlite:///{db_path_str}"

    # Patch the DB_NAME and DATABASE_URL to use test database
    monkeypatch.setenv("DATABASE_URL", db_url)
    import database.db_connection
    original_db_name = database.db_connection.DB_NAME
    database.db_connection.DB_NAME = db_url

    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url

    # Run Alembic migrations programmatically
    from alembic.config import Config
    from alembic import command
    with app.app_context():
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        command.upgrade(alembic_cfg, "head")

    yield app

    # Clean up and close engine connections (crucial for SQLite on Windows)
    with app.app_context():
        from database.models import db
        db.session.remove()
        db.engine.dispose()

    # Restore original DB_NAME
    database.db_connection.DB_NAME = original_db_name
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass


@pytest.fixture
def client(app):
    """Create a Flask test client authenticated with a seeded organization admin user."""
    c = app.test_client()
    with app.app_context():
        from database.models import db, User
        existing = db.session.query(User).filter(User.email == "admin@example.com").first()
        if existing is None:
            existing = User(name="Test Admin", email="admin@example.com", role="admin", organization_id=1)
            existing.set_password("secret")
            db.session.add(existing)
            db.session.commit()
        else:
            existing.set_password("secret")
            db.session.commit()

    response = c.post("/login", data={"email": "admin@example.com", "password": "secret"}, follow_redirects=True)
    assert response.status_code in (200, 302)
    return c


@pytest.fixture
def runner(app):
    """Create a CLI test runner."""
    return app.test_cli_runner()
