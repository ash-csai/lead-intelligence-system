"""Alembic initialization and configuration."""

import os
from alembic import command
from alembic.config import Config


def init_alembic():
    """Initialize Alembic for the project if not already done."""
    alembic_dir = "alembic"
    
    if not os.path.exists(alembic_dir):
        config = Config()
        config.set_main_option("script_location", alembic_dir)
        config.set_main_option("sqlalchemy.url", os.environ.get("DATABASE_URL", "sqlite:///lead_system.db"))
        command.init(config, alembic_dir)
        print(f"Alembic initialized at {alembic_dir}")
    else:
        print(f"Alembic already initialized at {alembic_dir}")


if __name__ == "__main__":
    init_alembic()
