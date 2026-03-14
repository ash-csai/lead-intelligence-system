import sqlite3

DB_NAME = "lead_system.db"

def init_database():
    conn = sqlite3.connect(DB_NAME)

    with open("database/schema.sql", "r") as f:
        conn.executescript(f.read())

    conn.close()
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_database()