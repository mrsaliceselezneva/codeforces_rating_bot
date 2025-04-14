import sqlite3
from contextlib import contextmanager

DB_PATH = "/app/data.db"


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()
