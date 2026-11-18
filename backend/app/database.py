import sqlite3
from contextlib import closing
from pathlib import Path

DATABASE_PATH = Path(__file__).resolve().parents[2] / "infra" / "data" / "planner.sqlite3"


def initialize_database() -> None:
    from . import planner_store

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        connection.execute("PRAGMA journal_mode = WAL").fetchone()
        planner_store.initialize(connection)
        connection.execute("CREATE TABLE IF NOT EXISTS companies (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)")
        connection.execute("CREATE TABLE IF NOT EXISTS resumes (id TEXT PRIMARY KEY, document TEXT NOT NULL)")
        connection.execute("CREATE TABLE IF NOT EXISTS company_analyses (id TEXT PRIMARY KEY, company_id INTEGER NOT NULL, data TEXT NOT NULL)")
        connection.execute("CREATE TABLE IF NOT EXISTS resume_fits (id TEXT PRIMARY KEY, company_id INTEGER NOT NULL, data TEXT NOT NULL)")
        connection.execute("CREATE TABLE IF NOT EXISTS cover_letters (id TEXT PRIMARY KEY, company_id INTEGER NOT NULL, data TEXT NOT NULL)")


def check_database() -> None:
    with closing(sqlite3.connect(f"{DATABASE_PATH.as_uri()}?mode=ro", uri=True)) as connection:
        connection.execute("PRAGMA user_version").fetchone()
