import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB = BASE_DIR / "lead_system.db"


def default_sqlite_uri():
    """Return the repository-local SQLite URI used only as a convenience fallback."""
    return f"sqlite:///{DEFAULT_DB.as_posix()}"


class Config:
    """Base Flask configuration.

    Keep secrets out of the repository and drive every value from the
    environment or a standard default that is safe in production.
    """

    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    DEBUG = False
    TESTING = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", default_sqlite_uri())


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", default_sqlite_uri())


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", default_sqlite_uri())


class TestingConfig(Config):
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
