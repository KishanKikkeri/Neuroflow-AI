"""
adk_agent/neuroflow_app/tools.py
---------------------------------
All FunctionTools that the ADK agents can call.
Each function must be synchronous (ADK calls them from its own executor)
or be an async def — ADK handles both.

Naming convention: <domain>_<verb>  e.g. task_add, note_list, calendar_create
"""

import json
import logging
from datetime import date, timedelta
from typing import Optional

from database.db import (
    add_note,
    add_task,
    get_notes,
    get_tasks,
    update_task_status,
)

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════════════
# TASK TOOLS
# ════════════════════════════════════════════════════════════════════════════════

def task_add(task: str, due_date: Optional[str] = None, status: str = "pending") -> str:
    """
    Add a new task to the database.

    Args:
        task: Description of the task.
        due_date: Optional due date in YYYY-MM-DD format.
        status: Task status — 'pending', 'in_progress', or 'done'. Default: 'pending'.

    Returns:
        Confirmation message with the new task id.
    """
    try:
        row = add_task(task=task, due_date=due_date, status=status)
        return (
            f"Task added successfully! ID: {row['id']} | "
            f"Task: {row['task']} | Due: {row.get('due_date', 'N/A')} | Status: {row['status']}"
        )
    except Exception as exc:
        logger.error("task_add failed: %s", exc)
        return f"Error adding task: {exc}"


def task_list(status: Optional[str] = None) -> str:
    """
    Retrieve tasks from the database.

    Args:
        status: Optional filter — 'pending', 'in_progress', or 'done'.
                Omit to fetch all tasks.

    Returns:
        JSON-formatted list of tasks.
    """
    try:
        tasks = get_tasks(status=status)
        if not tasks:
            return "No tasks found."
        return json.dumps(tasks, default=str, indent=2)
    except Exception as exc:
        logger.error("task_list failed: %s", exc)
        return f"Error fetching tasks: {exc}"


def task_update_status(task_id: int, status: str) -> str:
    """
    Update the status of an existing task.

    Args:
        task_id: Numeric id of the task to update.
        status: New status — 'pending', 'in_progress', or 'done'.

    Returns:
        Confirmation message.
    """
    try:
        row = update_task_status(task_id=task_id, status=status)
        return f"Task {row['id']} updated: '{row['task']}' → {row['status']}"
    except Exception as exc:
        logger.error("task_update_status failed: %s", exc)
        return f"Error updating task: {exc}"


# ════════════════════════════════════════════════════════════════════════════════
# NOTES TOOLS
# ════════════════════════════════════════════════════════════════════════════════

def note_add(content: str) -> str:
    """
    Save a new note to the database.

    Args:
        content: Full text of the note.

    Returns:
        Confirmation message with the new note id.
    """
    try:
        row = add_note(content=content)
        return f"Note saved! ID: {row['id']} | Created at: {row['created_at']}"
    except Exception as exc:
        logger.error("note_add failed: %s", exc)
        return f"Error saving note: {exc}"


def note_list(limit: int = 10) -> str:
    """
    Retrieve recent notes from the database.

    Args:
        limit: Maximum number of notes to return (default: 10).

    Returns:
        JSON-formatted list of notes.
    """
    try:
        notes = get_notes(limit=limit)
        if not notes:
            return "No notes found."
        return json.dumps(notes, default=str, indent=2)
    except Exception as exc:
        logger.error("note_list failed: %s", exc)
        return f"Error fetching notes: {exc}"


# ════════════════════════════════════════════════════════════════════════════════
# SMART DAY PLANNER HELPER TOOL
# ════════════════════════════════════════════════════════════════════════════════

def get_tomorrow_date() -> str:
    """
    Return tomorrow's date as a YYYY-MM-DD string.
    Used by the Smart Day Planner to resolve relative date references.

    Returns:
        Tomorrow's date string, e.g. '2025-01-16'.
    """
    tomorrow = date.today() + timedelta(days=1)
    return tomorrow.strftime("%Y-%m-%d")


def get_today_date() -> str:
    """
    Return today's date as a YYYY-MM-DD string.

    Returns:
        Today's date string, e.g. '2025-01-15'.
    """
    return date.today().strftime("%Y-%m-%d")
