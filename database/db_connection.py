import sqlite3
from flask import g

DB_NAME = "lead_system.db"

def get_db():
    if "db" not in g:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
