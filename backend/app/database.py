import sqlite3
from contextlib import closing
from pathlib import Path

DATABASE_PATH = Path(__file__).resolve().parents[2] / "infra" / "data" / "planner.sqlite3"


def initialize_database() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        connection.execute("PRAGMA journal_mode = WAL").fetchone()
        connection.execute("CREATE TABLE IF NOT EXISTS companies (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)")


def check_database() -> None:
    with closing(sqlite3.connect(f"{DATABASE_PATH.as_uri()}?mode=ro", uri=True)) as connection:
        connection.execute("PRAGMA user_version").fetchone()
