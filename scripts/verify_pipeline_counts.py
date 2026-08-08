import os, sys
from pathlib import Path

sys.path.insert(0, str(Path('.').resolve()))
from app import create_app
from database.db_connection import get_db
from modules.analytics_engine import get_pipeline_counts

# Use the application DB connection to ensure same environment
app = create_app()
with app.app_context():
    db = get_db()
    counts = get_pipeline_counts(db)
    print(counts)
