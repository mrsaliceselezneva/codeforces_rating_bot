import sqlite3

DB_PATH = "/app/data.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            handle TEXT PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            telegram_id INTEGER,
            is_admin INTEGER NOT NULL DEFAULT 0,
            rank TEXT DEFAULT '',
            top_rank TEXT DEFAULT '',
            rating INTEGER DEFAULT 0,
            last_updated TEXT DEFAULT ''
        )
    """)

    conn.commit()
    conn.close()
