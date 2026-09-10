"""Alembic migration environment configuration."""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

# Add the parent directory to path so we can import our models
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.models import db

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add the models' MetaData object for 'autogenerate' support
target_metadata = db.metadata

# Set the sqlalchemy url from environment or default. PostgreSQL URLs should be
# supplied as `postgresql+psycopg://...` or `postgresql+psycopg2://...` and
# the SQLite file is only a local convenience fallback. Keep the migration
# environment aligned with the project config chain.
sqlalchemy_url = os.environ.get("DATABASE_URL", "sqlite:///lead_system.db")
if sqlalchemy_url:
    config.set_main_option("sqlalchemy.url", sqlalchemy_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (doesn't need a live database)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (requires live database connection)."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = config.get_main_option("sqlalchemy.url")

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
