import sys
import os

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app

app = create_app()

for r in sorted(app.url_map.iter_rules(), key=lambda x: x.rule):
    print(f"{r.endpoint} -> {r.rule}")
