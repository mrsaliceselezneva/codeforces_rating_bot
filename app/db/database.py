import sqlite3
from contextlib import contextmanager
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "../../data.db")


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()
