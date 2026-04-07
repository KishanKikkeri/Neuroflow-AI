"""
adk_agent/neuroflow_app/sub_agents.py
--------------------------------------
Defines the four specialist sub-agents used by the NeuroFlow coordinator:

  1. TaskAgent        — AlloyDB task CRUD
  2. NotesAgent       — AlloyDB notes CRUD
  3. CalendarAgent    — Google Calendar via MCP
  4. SmartDayPlanner  — multi-step orchestration agent

Each sub-agent is a google.adk.agents.LlmAgent with its own system prompt
and a focused tool set.
"""

import logging

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from config.settings import GEMINI_MODEL
from tools.calendar_mcp import build_calendar_toolset
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


# ════════════════════════════════════════════════════════════════════════════════
# 1. TASK AGENT
# ════════════════════════════════════════════════════════════════════════════════

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


# ════════════════════════════════════════════════════════════════════════════════
# 2. NOTES AGENT
# ════════════════════════════════════════════════════════════════════════════════

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


# ════════════════════════════════════════════════════════════════════════════════
# 3. CALENDAR AGENT (MCP)
# ════════════════════════════════════════════════════════════════════════════════

def _build_calendar_agent() -> LlmAgent:
    """
    Build the CalendarAgent with a fresh MCP toolset.
    Called at startup so the bearer token is refreshed.
    """
    calendar_toolset = build_calendar_toolset()

    return LlmAgent(
        name="CalendarAgent",
        model=GEMINI_MODEL,
        description=(
            "Specialist agent for Google Calendar. "
            "Creates and retrieves calendar events via the Calendar MCP server."
        ),
        instruction="""
You are the Calendar Manager for NeuroFlow AI.
Your sole responsibility is interacting with Google Calendar via MCP tools.

CAPABILITIES:
- Create a new calendar event (summary, start/end datetime, description)
- List/fetch events for a given date or time range

RULES:
- Always convert relative times ("tomorrow at 5pm") to ISO 8601 datetimes
  before calling MCP tools.
- Default event duration is 1 hour unless stated otherwise.
- Confirm back to the user with event title, date, and time after creation.
- If the user asks about tasks or notes, redirect them to the appropriate agent.

DATETIME FORMAT: "YYYY-MM-DDTHH:MM:SS"  (e.g. "2025-01-16T17:00:00")
""",
        tools=[calendar_toolset],
    )


calendar_agent = _build_calendar_agent()


# ════════════════════════════════════════════════════════════════════════════════
# 4. SMART DAY PLANNER AGENT
# ════════════════════════════════════════════════════════════════════════════════

def _build_smart_planner() -> LlmAgent:
    """
    The Smart Day Planner pulls data from DB, Calendar, and Weather,
    then synthesises a structured daily plan for the user.
    """
    calendar_toolset = build_calendar_toolset()

    return LlmAgent(
        name="SmartDayPlannerAgent",
        model=GEMINI_MODEL,
        description=(
            "Multi-source orchestration agent that builds a smart daily plan "
            "by combining tasks from AlloyDB, events from Google Calendar, "
            "and optional weather data."
        ),
        instruction="""
You are the Smart Day Planner for NeuroFlow AI.
When asked to "plan my day" or similar, you must:

STEP 1 — Determine the target date:
  - If the user says "tomorrow", call get_tomorrow_date().
  - If the user says "today", call get_today_date().

STEP 2 — Gather data in parallel conceptually (call each tool):
  a) Call task_list() to get pending/in-progress tasks.
  b) Use the Calendar MCP tool to fetch events for the target date.
  c) Optionally call weather_tool_fn() for the user's city.

STEP 3 — Synthesise a structured daily plan:
  Format the output as:

  ╔══════════════════════════════════════════╗
  ║  📅  SMART DAY PLAN — [DATE]            ║
  ╚══════════════════════════════════════════╝

  🌤️  WEATHER
  [weather summary or "Weather data unavailable"]

  📅  CALENDAR EVENTS
  [list of events with times]

  ✅  TASKS FOR THE DAY
  [prioritised task list]

  💡  AI RECOMMENDATIONS
  [2-3 actionable tips based on the data]

RULES:
- Always call the tools — never hallucinate data.
- If a data source fails, note it gracefully and continue.
- Keep the plan concise, actionable, and positive in tone.
""",
        tools=[
            FunctionTool(func=task_list),
            FunctionTool(func=get_tomorrow_date),
            FunctionTool(func=get_today_date),
            FunctionTool(func=weather_tool_fn),
            calendar_toolset,
        ],
    )


smart_day_planner_agent = _build_smart_planner()
