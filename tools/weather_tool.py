"""
tools/weather_tool.py
---------------------
Optional weather tool used by the Smart Day Planner.
Calls the free OpenWeatherMap Current Weather API (v2.5).

If OPENWEATHER_API_KEY is not set, returns a graceful fallback
so the system still works without a weather key.
"""

import logging
from typing import Any

import httpx

from config.settings import OPENWEATHER_API_KEY, WEATHER_CITY

logger = logging.getLogger(__name__)

OWMAP_URL = "https://api.openweathermap.org/data/2.5/weather"


async def get_weather(city: str = WEATHER_CITY) -> dict[str, Any]:
    """
    Fetch current weather for *city*.
    Returns a clean dict; never raises (returns error key instead).
    """
    if not OPENWEATHER_API_KEY:
        logger.warning("OPENWEATHER_API_KEY not set — skipping weather.")
        return {"error": "Weather API key not configured.", "city": city}

    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",   # °C; change to "imperial" for °F
    }

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(OWMAP_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        result = {
            "city": data.get("name", city),
            "condition": data["weather"][0]["description"].capitalize(),
            "temperature_c": data["main"]["temp"],
            "feels_like_c": data["main"]["feels_like"],
            "humidity_pct": data["main"]["humidity"],
            "wind_kmh": round(data["wind"]["speed"] * 3.6, 1),
        }
        logger.info("Weather fetched for %s: %s", city, result["condition"])
        return result

    except httpx.HTTPStatusError as exc:
        logger.error("Weather API HTTP error: %s", exc)
        return {"error": f"HTTP {exc.response.status_code}", "city": city}
    except Exception as exc:
        logger.error("Weather fetch failed: %s", exc)
        return {"error": str(exc), "city": city}


# ── ADK-compatible function tool wrapper ──────────────────────────────────────
# This can be added directly to an agent's tools list.

def weather_tool_fn(city: str = WEATHER_CITY) -> str:
    """
    ADK FunctionTool shim — runs the async helper in the current event loop.
    Returns a plain string summary for the agent.
    """
    import asyncio
    import json

    data = asyncio.get_event_loop().run_until_complete(get_weather(city))
    if "error" in data:
        return f"Weather unavailable: {data['error']}"
    return (
        f"Weather in {data['city']}: {data['condition']}, "
        f"{data['temperature_c']}°C (feels like {data['feels_like_c']}°C), "
        f"humidity {data['humidity_pct']}%, wind {data['wind_kmh']} km/h."
    )
