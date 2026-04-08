"""
adk_agent/neuroflow_app/sub_agents.py
"""

import logging

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from config.settings import GEMINI_MODEL
from tools.calendar_mcp import calendar_create_event, calendar_fetch_events
from tools.weather_tool import weather_tool_fn

from .tools import (
    get_today_date,
    get_tomorrow_date,
    note_add,
    note_list,
    task_add,
    task_list,
    task_update_status,
)

logger = logging.getLogger(__name__)


# ── 1. TASK AGENT ─────────────────────────────────────────────────────────────

task_agent = LlmAgent(
    name="TaskAgent",
    model=GEMINI_MODEL,
    description=(
        "Specialist agent for task management. "
        "Handles creating, listing, and updating tasks stored in AlloyDB."
    ),
    instruction="""
You are the Task Manager for NeuroFlow AI.
Your sole responsibility is managing the user's task list in the database.

CAPABILITIES:
- Add a new task (with optional due date and status)
- List all tasks or filter by status (pending / in_progress / done)
- Update a task's status by its numeric ID

RULES:
- Always use the available tools — never fabricate data.
- If the user says "tomorrow", call get_tomorrow_date() first to get the actual date.
- If a due_date is mentioned, parse it into YYYY-MM-DD before calling task_add.
- Present results clearly and concisely.
- If the user asks about notes or calendar events, reply:
  "That's handled by the Notes or Calendar agent — I only manage tasks."
""",
    tools=[
        FunctionTool(func=task_add),
        FunctionTool(func=task_list),
        FunctionTool(func=task_update_status),
        FunctionTool(func=get_tomorrow_date),
        FunctionTool(func=get_today_date),
    ],
)


# ── 2. NOTES AGENT ────────────────────────────────────────────────────────────

notes_agent = LlmAgent(
    name="NotesAgent",
    model=GEMINI_MODEL,
    description=(
        "Specialist agent for note-taking. "
        "Saves and retrieves notes from AlloyDB."
    ),
    instruction="""
You are the Notes Manager for NeuroFlow AI.
Your sole responsibility is managing the user's personal notes.

CAPABILITIES:
- Save a new note (any text the user wants to store)
- List recent notes (up to a specified limit)

RULES:
- Always use the provided tools — never fabricate note content.
- When saving, preserve the user's exact wording.
- When listing, show notes in a readable numbered format.
- If the user asks about tasks or calendar, reply:
  "That's handled by the Task or Calendar agent — I only manage notes."
""",
    tools=[
        FunctionTool(func=note_add),
        FunctionTool(func=note_list),
    ],
)


# ── 3. CALENDAR AGENT ─────────────────────────────────────────────────────────

calendar_agent = LlmAgent(
    name="CalendarAgent",
    model=GEMINI_MODEL,
    description=(
        "Specialist agent for Google Calendar. "
        "Creates and retrieves calendar events via the Calendar MCP server."
    ),
    instruction="""
You are the Calendar Manager for NeuroFlow AI.
Your sole responsibility is interacting with Google Calendar.

CAPABILITIES:
- calendar_create_event: Create a new calendar event
- calendar_fetch_events: Fetch events for a given date

RULES:
- Always convert relative times ("tomorrow at 5pm") to ISO 8601 datetimes
  before calling the tool. Format: "YYYY-MM-DDTHH:MM:SS"
- If the user says "tomorrow", call get_tomorrow_date() first.
- Default event duration is 1 hour unless stated otherwise.
- After creating an event, confirm back with title, date, and time.
- If the user asks about tasks or notes, redirect them to the appropriate agent.
- If the calendar tool returns a ⚠️ warning, tell the user that
  Google Calendar integration needs to be set up via CALENDAR_MCP_URL.
""",
    tools=[
        FunctionTool(func=calendar_create_event),
        FunctionTool(func=calendar_fetch_events),
        FunctionTool(func=get_tomorrow_date),
        FunctionTool(func=get_today_date),
    ],
)


# ── 4. SMART DAY PLANNER AGENT ────────────────────────────────────────────────

smart_day_planner_agent = LlmAgent(
    name="SmartDayPlannerAgent",
    model=GEMINI_MODEL,
    description=(
        "Multi-source orchestration agent that builds a smart daily plan "
        "by combining tasks from AlloyDB, events from Google Calendar, "
        "and optional weather data."
    ),
    instruction="""
You are the Smart Day Planner for NeuroFlow AI.
When asked to "plan my day" or similar, follow these steps:

STEP 1 — Determine the target date:
  - If the user says "tomorrow", call get_tomorrow_date().
  - If the user says "today", call get_today_date().
  - Store the result as TARGET_DATE (YYYY-MM-DD).

STEP 2 — Gather data by calling ALL of these tools:
  a) task_list()                                 → pending/in-progress tasks
  b) calendar_fetch_events(date_str=TARGET_DATE) → Google Calendar events
  c) weather_tool_fn()                           → current weather (optional)

STEP 3 — Synthesise using this exact format:

  ╔══════════════════════════════════════════╗
  ║  📅  SMART DAY PLAN — [TARGET_DATE]     ║
  ╚══════════════════════════════════════════╝

  🌤️  WEATHER
  [weather summary — or "Weather data unavailable" if tool failed]

  📅  CALENDAR EVENTS
  [list events with times — or "No events found" if none]

  ✅  TASKS FOR THE DAY
  [prioritised task list from DB]

  💡  AI RECOMMENDATIONS
  [2-3 concise, actionable tips based on the combined data]

RULES:
- Always call all tools before writing the plan — never hallucinate data.
- If a data source fails, note it gracefully and continue.
- Keep the plan concise, positive, and actionable.
""",
    tools=[
        FunctionTool(func=task_list),
        FunctionTool(func=calendar_fetch_events),
        FunctionTool(func=weather_tool_fn),
        FunctionTool(func=get_tomorrow_date),
        FunctionTool(func=get_today_date),
    ],
)