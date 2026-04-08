"""
tools/calendar_mcp.py
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import google.auth
import google.auth.transport.requests

from config.settings import CALENDAR_MCP_URL, CALENDAR_SCOPES

logger = logging.getLogger(__name__)


def _get_bearer_token() -> str:
    credentials, _ = google.auth.default(scopes=CALENDAR_SCOPES)
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    return credentials.token


def _is_mcp_configured() -> bool:
    return bool(CALENDAR_MCP_URL) and not CALENDAR_MCP_URL.startswith(
        "https://calendar-mcp-server-<"
    )


def _make_toolset():
    from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
    from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

    token = _get_bearer_token()
    return MCPToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=CALENDAR_MCP_URL,
            headers={"Authorization": f"Bearer {token}"},
        )
    )


async def calendar_create_event(
    summary: str,
    start_datetime: str,
    end_datetime: str,
    description: str = "",
    timezone_str: str = "Asia/Kolkata",
) -> str:
    """
    Create a Google Calendar event.

    Args:
        summary: Event title / name.
        start_datetime: Start in ISO 8601, e.g. '2025-01-16T14:00:00'.
        end_datetime: End in ISO 8601, e.g. '2025-01-16T15:00:00'.
        description: Optional event description or agenda.
        timezone_str: IANA timezone, e.g. 'Asia/Kolkata'. Default: Asia/Kolkata.

    Returns:
        Confirmation string with event details, or a clear error message.
    """
    if not _is_mcp_configured():
        return (
            "⚠️ Google Calendar is not connected yet. "
            "Please set CALENDAR_MCP_URL in the environment variables."
        )
    try:
        toolset = _make_toolset()
        async with toolset as ts:
            tools = await ts.get_tools()
            create_tool = next(
                (t for t in tools if "create" in t.name.lower()), None
            )
            if not create_tool:
                return "Calendar MCP server does not expose a 'create event' tool."

            result = await create_tool.run_async(
                args={
                    "summary": summary,
                    "start": {"dateTime": start_datetime, "timeZone": timezone_str},
                    "end":   {"dateTime": end_datetime,   "timeZone": timezone_str},
                    "description": description,
                },
                tool_context=None,
            )
        logger.info("Calendar event created: %s", summary)
        return (
            f"✅ Event '{summary}' created! "
            f"Start: {start_datetime} | End: {end_datetime} | Details: {result}"
        )
    except Exception as exc:
        logger.error("calendar_create_event failed: %s", exc)
        return f"Failed to create calendar event: {exc}"


async def calendar_fetch_events(
    date_str: Optional[str] = None,
    max_results: int = 10,
) -> str:
    """
    Fetch Google Calendar events for a specific date.

    Args:
        date_str: Date in YYYY-MM-DD format. Defaults to today.
        max_results: Maximum number of events to return. Default: 10.

    Returns:
        Formatted string listing events, or a message if none found / error.
    """
    if not _is_mcp_configured():
        return (
            "⚠️ Google Calendar is not connected yet. "
            "Please set CALENDAR_MCP_URL in the environment variables."
        )

    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    day_start = datetime.fromisoformat(f"{date_str}T00:00:00+00:00")
    day_end   = day_start + timedelta(days=1)

    try:
        toolset = _make_toolset()
        async with toolset as ts:
            tools = await ts.get_tools()
            list_tool = next(
                (t for t in tools if "list" in t.name.lower() or "get" in t.name.lower()),
                None,
            )
            if not list_tool:
                return "Calendar MCP server does not expose a 'list events' tool."

            result = await list_tool.run_async(
                args={
                    "timeMin":      day_start.isoformat(),
                    "timeMax":      day_end.isoformat(),
                    "maxResults":   max_results,
                    "singleEvents": True,
                    "orderBy":      "startTime",
                },
                tool_context=None,
            )

        events: list[dict[str, Any]] = (
            result if isinstance(result, list) else result.get("items", [])
        )

        if not events:
            return f"No calendar events found for {date_str}."

        lines = [f"📅 Calendar events for {date_str}:"]
        for ev in events:
            start = (
                ev.get("start", {}).get("dateTime")
                or ev.get("start", {}).get("date", "?")
            )
            lines.append(f"  • {ev.get('summary', 'Untitled')} @ {start}")

        logger.info("Fetched %d events for %s", len(events), date_str)
        return "\n".join(lines)

    except Exception as exc:
        logger.error("calendar_fetch_events failed: %s", exc)
        return f"Failed to fetch calendar events: {exc}"