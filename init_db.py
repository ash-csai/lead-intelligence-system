import os
from alembic.config import Config
from alembic import command

def init_database():
    # Setup Alembic Config using alembic.ini
    alembic_cfg = Config("alembic.ini")
    
    # Override sqlalchemy.url with the environment variable if present
    db_url = os.environ.get("DATABASE_URL", "sqlite:///lead_system.db")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    
    print(f"Applying Alembic migrations on {db_url}...")
    command.upgrade(alembic_cfg, "head")
    print("Database initialized successfully via Alembic migrations!")

if __name__ == "__main__":
    init_database()