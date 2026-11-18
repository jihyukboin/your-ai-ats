"""SQLite storage for planner calendar entries, conversation memory, and immutable events."""

import json
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from uuid import uuid4

from . import database


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def initialize(connection):
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS planner_memory (
            session_id TEXT PRIMARY KEY,
            revision INTEGER NOT NULL,
            data TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS planner_events (
            id INTEGER PRIMARY KEY,
            session_id TEXT NOT NULL,
            run_id TEXT NOT NULL,
            seq INTEGER NOT NULL,
            at TEXT NOT NULL,
            event TEXT NOT NULL,
            UNIQUE(run_id, seq)
        );
        CREATE INDEX IF NOT EXISTS planner_events_session ON planner_events(session_id, id);
        CREATE TABLE IF NOT EXISTS planner_plans (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            notes TEXT NOT NULL,
            url TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS planner_plans_date ON planner_plans(date, start_time);
    """)


@contextmanager
def connection():
    with closing(sqlite3.connect(database.DATABASE_PATH)) as db, db:
        db.row_factory = sqlite3.Row
        yield db


def load_memory(session_id):
    with connection() as db:
        row = db.execute("SELECT revision, data FROM planner_memory WHERE session_id=?", (session_id,)).fetchone()
    return (row["revision"], json.loads(row["data"])) if row else (0, {})


def save_memory(session_id, revision, memory):
    data = json.dumps(memory, ensure_ascii=False)
    with connection() as db:
        if revision == 0:
            change = db.execute("INSERT OR IGNORE INTO planner_memory VALUES (?, 1, ?)", (session_id, data))
        else:
            change = db.execute(
                "UPDATE planner_memory SET data=?, revision=revision+1 WHERE session_id=? AND revision=?",
                (data, session_id, revision),
            )
        return change.rowcount == 1


def append_event(event):
    with connection() as db:
        db.execute(
            """INSERT INTO planner_events(session_id,run_id,seq,at,event)
               SELECT :session_id,:run_id,:seq,:at,:encoded
               WHERE :seq=1 OR EXISTS (SELECT 1 FROM planner_events WHERE run_id=:run_id)""",
            {**event, "encoded": json.dumps(event, ensure_ascii=False)},
        )


def log_sessions():
    with connection() as db:
        rows = db.execute("""
            SELECT session_id, COUNT(DISTINCT run_id) AS run_count,
                   COUNT(*) AS event_count, MAX(at) AS updated_at
            FROM planner_events GROUP BY session_id ORDER BY MAX(id) DESC
        """)
        return [dict(row) for row in rows]


def session_log(session_id):
    with connection() as db:
        rows = db.execute("SELECT event FROM planner_events WHERE session_id=? ORDER BY id", (session_id,))
        runs = {}
        for row in rows:
            event = json.loads(row["event"])
            run_id = event["run_id"]
            run = runs.setdefault(run_id, dict(run_id=run_id, started_at=event["at"], events=[]))
            run["events"].append(event)
            if event["type"] == "chat_started":
                run["message"] = event["data"]["message"]
            if event["type"] == "chat_completed":
                run.update(event["data"])
    return {"session_id": session_id, "runs": list(runs.values())} if runs else None


def delete_log(session_id):
    with connection() as db:
        return db.execute("DELETE FROM planner_events WHERE session_id=?", (session_id,)).rowcount > 0


def list_plans():
    with connection() as db:
        return [dict(row) for row in db.execute("SELECT * FROM planner_plans ORDER BY date, start_time, created_at")]


def get_plan(plan_id):
    with connection() as db:
        row = db.execute("SELECT * FROM planner_plans WHERE id=?", (plan_id,)).fetchone()
        return dict(row) if row else None


def write_plan(values, plan_id=None):
    now = utc_now()
    with connection() as db:
        if plan_id is None:
            plan_id = str(uuid4())
            db.execute("""
                INSERT INTO planner_plans(id,title,date,start_time,end_time,notes,url,created_at,updated_at)
                VALUES(:id,:title,:date,:start_time,:end_time,:notes,:url,:now,:now)
            """, {**values, "id": plan_id, "now": now})
        else:
            updated = db.execute("""
                UPDATE planner_plans SET title=:title,date=:date,start_time=:start_time,end_time=:end_time,
                                         notes=:notes,url=:url,updated_at=:now WHERE id=:id
            """, {**values, "id": plan_id, "now": now})
            if not updated.rowcount:
                return None
        plan = dict(db.execute("SELECT * FROM planner_plans WHERE id=?", (plan_id,)).fetchone())
        overlaps = db.execute("""
            SELECT * FROM planner_plans WHERE date=:date AND start_time<:end_time AND end_time>:start_time
                                        AND id!=:id ORDER BY start_time,created_at
        """, plan)
        return {"plan": plan, "overlaps": [dict(row) for row in overlaps]}


def delete_plan(plan_id):
    with connection() as db:
        return db.execute("DELETE FROM planner_plans WHERE id=?", (plan_id,)).rowcount > 0
