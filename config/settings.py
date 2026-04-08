import os
from dotenv import load_dotenv

load_dotenv()  # loads .env in local dev; Cloud Run uses native env vars

# ── Google / Gemini ────────────────────────────────────────────────────────────
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "neuroflow-ai-492705")
GOOGLE_CLOUD_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")          # for local dev
# Setting default to 2.5-flash as requested
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# ── Database (Now using Firestore) ─────────────────────────────────────────────
DATABASE_TYPE = os.environ.get("DATABASE_TYPE", "firestore")

# ── Google Calendar MCP ───────────────────────────────────────────────────────
CALENDAR_MCP_URL = os.environ.get(
    "CALENDAR_MCP_URL",
    "" # Leave empty if not yet deployed to avoid errors
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