"""
config/settings.py
------------------
Central configuration loader.
All secrets come from environment variables — never hardcoded.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # loads .env in local dev; Cloud Run uses native env vars

# ── Google / Gemini ────────────────────────────────────────────────────────────
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
GOOGLE_CLOUD_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")          # for local dev
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# ── AlloyDB (PostgreSQL) ───────────────────────────────────────────────────────
ALLOYDB_HOST = os.environ.get("ALLOYDB_HOST", "127.0.0.1")
ALLOYDB_PORT = int(os.environ.get("ALLOYDB_PORT", "5432"))
ALLOYDB_USER = os.environ.get("ALLOYDB_USER", "postgres")
ALLOYDB_PASSWORD = os.environ.get("ALLOYDB_PASSWORD", "")
ALLOYDB_DATABASE = os.environ.get("ALLOYDB_DATABASE", "neuroflow")

# ── Google Calendar MCP ───────────────────────────────────────────────────────
CALENDAR_MCP_URL = os.environ.get(
    "CALENDAR_MCP_URL",
    "https://calendar-mcp-server-<your-hash>-uc.a.run.app/mcp"
)
CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]

# ── API Server ─────────────────────────────────────────────────────────────────
PORT = int(os.environ.get("PORT", "8080"))
HOST = os.environ.get("HOST", "0.0.0.0")

# ── Optional: OpenWeather ─────────────────────────────────────────────────────
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")
WEATHER_CITY = os.environ.get("WEATHER_CITY", "San Francisco")