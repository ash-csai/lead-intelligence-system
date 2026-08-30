"""Pytest configuration and fixtures for Lead Intelligence System tests."""

import sqlite3
import tempfile
from pathlib import Path

import pytest
from app import create_app


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    
    # Initialize schema
    schema_sql = Path(__file__).parent.parent / "database" / "schema.sql"
    with open(schema_sql) as f:
        conn.executescript(f.read())
    
    conn.commit()
    
    yield conn
    
    conn.close()
    Path(db_path).unlink()


@pytest.fixture
def app(tmp_path, monkeypatch):
    """Create Flask app with temporary database for testing."""
    # Create temporary database
    db_path = tmp_path / "test.db"
    db_path_str = str(db_path)
    
    # Initialize database schema
    conn = sqlite3.connect(db_path_str)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    
    schema_sql = Path(__file__).parent.parent / "database" / "schema.sql"
    with open(schema_sql) as f:
        conn.executescript(f.read())
    
    conn.commit()
    conn.close()
    
    # Patch the DB_NAME to use test database
    monkeypatch.setenv("FLASK_TESTING", "true")
    import database.db_connection
    original_db_name = database.db_connection.DB_NAME
    database.db_connection.DB_NAME = db_path_str
    
    app = create_app()
    app.config["TESTING"] = True
    
    yield app
    
    # Restore original DB_NAME
    database.db_connection.DB_NAME = original_db_name


@pytest.fixture
def client(app):
    """Create a Flask test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a CLI test runner."""
    return app.test_cli_runner()
