"""
tools/calendar_mcp.py
---------------------
Google Calendar integration via the Model Context Protocol (MCP).

Uses google-auth Application Default Credentials (ADC) to obtain a bearer
token, then connects to a Calendar MCP server over StreamableHTTP.

The MCPToolset is designed to be used INSIDE an ADK agent's tools list.
We also expose thin async helper functions so the CalendarAgent can call
them directly for the "Smart Day Planner" workflow.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import google.auth
import google.auth.transport.requests

from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

from config.settings import CALENDAR_MCP_URL, CALENDAR_SCOPES

logger = logging.getLogger(__name__)


# ── Auth helper ───────────────────────────────────────────────────────────────

def _get_bearer_token() -> str:
    """
    Obtain a short-lived OAuth2 bearer token via Application Default Credentials.
    On Cloud Run this uses the attached service account automatically.
    Locally, run:  gcloud auth application-default login --scopes=...
    """
    credentials, _ = google.auth.default(scopes=CALENDAR_SCOPES)
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)
    return credentials.token


# ── MCPToolset factory ────────────────────────────────────────────────────────

def build_calendar_toolset() -> MCPToolset:
    """
    Return an MCPToolset pre-configured for the Calendar MCP server.
    This object is passed directly into an ADK agent's `tools` list.
    """
    token = _get_bearer_token()
    return MCPToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=CALENDAR_MCP_URL,
            headers={"Authorization": f"Bearer {token}"},
        )
    )


# ── Standalone async helpers (used by Smart Day Planner) ─────────────────────

async def create_calendar_event(
    summary: str,
    start_datetime: str,          # ISO 8601 e.g. "2025-01-15T14:00:00"
    end_datetime: str,
    description: str = "",
    timezone_str: str = "America/Los_Angeles",
) -> dict[str, Any]:
    """
    Create a Google Calendar event.
    Wraps the MCP tool call so non-agent code can use it directly.
    """
    from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
    toolset = build_calendar_toolset()

    async with toolset as ts:
        tools = await ts.get_tools()
        create_tool = next((t for t in tools if "create" in t.name.lower()), None)
        if not create_tool:
            raise RuntimeError("Calendar MCP server has no 'create event' tool.")

        result = await create_tool.run_async(
            args={
                "summary": summary,
                "start": {"dateTime": start_datetime, "timeZone": timezone_str},
                "end": {"dateTime": end_datetime, "timeZone": timezone_str},
                "description": description,
            },
            tool_context=None,
        )
    logger.info("Calendar event created: %s", summary)
    return result


async def fetch_calendar_events(
    date_str: Optional[str] = None,
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """
    Fetch upcoming Google Calendar events for a given date (YYYY-MM-DD).
    Defaults to today if date_str is None.
    """
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Build time window: full day in UTC
    day_start = datetime.fromisoformat(f"{date_str}T00:00:00+00:00")
    day_end = day_start + timedelta(days=1)

    toolset = build_calendar_toolset()
    async with toolset as ts:
        tools = await ts.get_tools()
        list_tool = next((t for t in tools if "list" in t.name.lower() or "get" in t.name.lower()), None)
        if not list_tool:
            raise RuntimeError("Calendar MCP server has no 'list events' tool.")

        result = await list_tool.run_async(
            args={
                "timeMin": day_start.isoformat(),
                "timeMax": day_end.isoformat(),
                "maxResults": max_results,
                "singleEvents": True,
                "orderBy": "startTime",
            },
            tool_context=None,
        )

    events = result if isinstance(result, list) else result.get("items", [])
    logger.info("Fetched %d calendar events for %s", len(events), date_str)
    return events