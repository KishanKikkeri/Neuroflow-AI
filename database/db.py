"""
database/db.py
--------------
AlloyDB (PostgreSQL) connection pool and CRUD helpers.
Uses psycopg2 with a simple connection-pool pattern that is safe for
single-process async servers (Cloud Run scales horizontally, not via threads).
"""

import logging
from contextlib import contextmanager
from datetime import date, datetime
from typing import List, Optional

import psycopg2
import psycopg2.extras
from psycopg2 import pool as pg_pool

from config.settings import (
    ALLOYDB_DATABASE,
    ALLOYDB_HOST,
    ALLOYDB_PASSWORD,
    ALLOYDB_PORT,
    ALLOYDB_USER,
)

logger = logging.getLogger(__name__)

# ── Connection pool (created lazily on first use) ─────────────────────────────
_pool: Optional[pg_pool.ThreadedConnectionPool] = None


def _get_pool() -> pg_pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        _pool = pg_pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            host=ALLOYDB_HOST,
            port=ALLOYDB_PORT,
            user=ALLOYDB_USER,
            password=ALLOYDB_PASSWORD,
            dbname=ALLOYDB_DATABASE,
        )
        logger.info("AlloyDB connection pool initialised.")
    return _pool


@contextmanager
def get_conn():
    """Yield a psycopg2 connection from the pool and auto-return it."""
    conn = _get_pool().getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _get_pool().putconn(conn)


# ── Tasks ─────────────────────────────────────────────────────────────────────

def add_task(task: str, due_date: Optional[str] = None, status: str = "pending") -> dict:
    """Insert a task and return the created row."""
    parsed_due: Optional[date] = None
    if due_date:
        try:
            parsed_due = datetime.strptime(due_date, "%Y-%m-%d").date()
        except ValueError:
            logger.warning("Invalid due_date format '%s', storing NULL.", due_date)

    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO tasks (task, due_date, status)
                VALUES (%s, %s, %s)
                RETURNING id, task, due_date::text, status, created_at::text
                """,
                (task, parsed_due, status),
            )
            row = cur.fetchone()
    logger.info("Task added: id=%s", row["id"])
    return dict(row)


def get_tasks(status: Optional[str] = None) -> List[dict]:
    """Return all tasks, optionally filtered by status."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if status:
                cur.execute(
                    "SELECT id, task, due_date::text, status, created_at::text "
                    "FROM tasks WHERE status = %s ORDER BY due_date NULLS LAST, id",
                    (status,),
                )
            else:
                cur.execute(
                    "SELECT id, task, due_date::text, status, created_at::text "
                    "FROM tasks ORDER BY due_date NULLS LAST, id"
                )
            return [dict(r) for r in cur.fetchall()]


def update_task_status(task_id: int, status: str) -> dict:
    """Update task status by id."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "UPDATE tasks SET status = %s WHERE id = %s "
                "RETURNING id, task, due_date::text, status",
                (status, task_id),
            )
            row = cur.fetchone()
    if not row:
        raise ValueError(f"Task id={task_id} not found.")
    return dict(row)


# ── Notes ─────────────────────────────────────────────────────────────────────

def add_note(content: str) -> dict:
    """Insert a note and return the created row."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO notes (content) VALUES (%s) "
                "RETURNING id, content, created_at::text",
                (content,),
            )
            row = cur.fetchone()
    logger.info("Note added: id=%s", row["id"])
    return dict(row)


def get_notes(limit: int = 20) -> List[dict]:
    """Return the most recent notes."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, content, created_at::text FROM notes "
                "ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
            return [dict(r) for r in cur.fetchall()]
