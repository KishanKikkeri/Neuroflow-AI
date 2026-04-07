# NeuroFlow AI 🧠

A production-ready **multi-agent AI system** built with **Google ADK**, **Gemini 2.5 Flash**,
**AlloyDB**, and **Google Calendar MCP** — deployable on **Google Cloud Run**.

---

## Architecture

```
User Request (HTTP)
        │
        ▼
┌───────────────────────────────────────────────┐
│             FastAPI  (api/main.py)            │  ← Port 8080 (Cloud Run)
│          InMemoryRunner  (ADK session)        │
└──────────────────────┬────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │   NeuroFlowCoordinator       │  ← root_agent (LlmAgent / Gemini)
        │   Intent detection & routing │
        └───┬──────┬────────┬──────────┘
            │      │        │          │
            ▼      ▼        ▼          ▼
      ┌──────┐ ┌──────┐ ┌───────┐ ┌──────────────┐
      │ Task │ │Notes │ │Calen- │ │SmartDayPlan- │
      │Agent │ │Agent │ │darAgt │ │nerAgent      │
      └──┬───┘ └──┬───┘ └───┬───┘ └──────┬───────┘
         │        │          │             │
         ▼        ▼          ▼             ▼
    AlloyDB   AlloyDB   Calendar MCP   AlloyDB +
    (tasks)   (notes)   (StreamHTTP)   Calendar MCP +
                                       Weather API
```

### Agent Responsibilities

| Agent | Responsibility | Data Source |
|-------|----------------|-------------|
| `NeuroFlowCoordinator` | Intent detection, routing, multi-step orchestration | — |
| `TaskAgent` | Add / list / update tasks | AlloyDB `tasks` table |
| `NotesAgent` | Save / retrieve notes | AlloyDB `notes` table |
| `CalendarAgent` | Create / fetch calendar events | Google Calendar MCP |
| `SmartDayPlannerAgent` | Unified daily plan synthesis | AlloyDB + Calendar MCP + Weather |

---

## Folder Structure

```
neuroflow_ai/
├── adk_agent/
│   └── neuroflow_app/
│       ├── __init__.py      # exposes root_agent for ADK
│       ├── agent.py         # NeuroFlowCoordinator (root_agent)
│       ├── sub_agents.py    # TaskAgent, NotesAgent, CalendarAgent, SmartDayPlannerAgent
│       └── tools.py         # FunctionTools wiring DB calls
│
├── database/
│   ├── db.py                # AlloyDB connection pool + CRUD
│   └── schema.sql           # One-time schema creation script
│
├── tools/
│   ├── calendar_mcp.py      # MCPToolset factory + async calendar helpers
│   └── weather_tool.py      # OpenWeatherMap async helper + ADK FunctionTool shim
│
├── api/
│   └── main.py              # FastAPI app + ADK InMemoryRunner
│
├── config/
│   └── settings.py          # Centralised env-var config
│
├── requirements.txt
├── .env.example
├── Dockerfile
└── README.md
```

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.12+ | Runtime |
| Google Cloud SDK (`gcloud`) | latest | Auth + deployment |
| AlloyDB / PostgreSQL | 15+ | Structured data |
| Google ADK | 1.0+ | Agent framework |
| Docker | 24+ | Container build |

---

## Local Development Setup

### 1. Clone and install dependencies

```bash
git clone <your-repo-url>
cd neuroflow_ai

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env and fill in all values (see .env.example for descriptions)
```

### 3. Set up AlloyDB / PostgreSQL

**Option A — Local PostgreSQL (for development):**
```bash
# Install PostgreSQL, then:
psql -U postgres -c "CREATE DATABASE neuroflow;"
psql -U postgres -d neuroflow -f database/schema.sql
```

**Option B — AlloyDB via Cloud SQL Auth Proxy:**
```bash
# Download: https://cloud.google.com/sql/docs/postgres/connect-auth-proxy
./cloud-sql-proxy \
  "${GOOGLE_CLOUD_PROJECT}:us-central1:neuroflow-instance" \
  --port 5432

# In a new terminal — apply schema:
psql -h 127.0.0.1 -U postgres -d neuroflow -f database/schema.sql
```

### 4. Authenticate with Google Cloud (for Calendar MCP + Gemini)

```bash
gcloud auth application-default login \
  --scopes="https://www.googleapis.com/auth/cloud-platform,\
https://www.googleapis.com/auth/calendar,\
https://www.googleapis.com/auth/calendar.events"
```

### 5. Deploy the Calendar MCP Server

The CalendarAgent needs a running MCP server that wraps the Google Calendar API.

```bash
# Clone the official Google MCP servers repo
git clone https://github.com/google/model-context-protocol-servers
cd model-context-protocol-servers/servers/google-calendar

# Deploy to Cloud Run
gcloud run deploy calendar-mcp-server \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT}"

# Copy the service URL into your .env:
# CALENDAR_MCP_URL=https://calendar-mcp-server-<hash>-uc.a.run.app/mcp
```

### 6. Run locally

```bash
# Option A — via Python directly
python -m uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload

# Option B — via ADK dev UI (lets you interact with agents in a browser)
cd adk_agent
adk web neuroflow_app
# Opens http://localhost:8000 with the ADK chat interface
```

---

## API Reference

### `POST /query` — Send a message to NeuroFlow AI

```bash
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Add a task: finish the report by 2025-01-20"}'
```

**Response:**
```json
{
  "session_id": "a1b2c3d4-...",
  "response": "Task added successfully! ID: 1 | Task: finish the report | Due: 2025-01-20 | Status: pending"
}
```

**Multi-turn conversation** — pass the session_id back:
```bash
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: a1b2c3d4-..." \
  -d '{"user_input": "What tasks do I have pending?"}'
```

---

### Example Requests by Intent

#### Tasks
```bash
# Add a task
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Add task: prepare presentation slides, due tomorrow"}'

# List all tasks
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Show me all my pending tasks"}'

# Update task status
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Mark task 1 as done"}'
```

#### Notes
```bash
# Save a note
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Save this note: The API key expires on the 30th"}'

# Retrieve notes
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Show my recent notes"}'
```

#### Calendar
```bash
# Schedule a meeting
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Schedule a meeting with the design team tomorrow at 3pm for 1 hour"}'

# Fetch events
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{"user_input": "What events do I have tomorrow?"}'
```

#### Smart Day Planner
```bash
# Full day plan
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Plan my day tomorrow"}'
```

**Example Smart Plan Response:**
```
╔══════════════════════════════════════════╗
║  📅  SMART DAY PLAN — 2025-01-16        ║
╚══════════════════════════════════════════╝

🌤️  WEATHER
Partly cloudy, 18°C (feels like 16°C), humidity 65%, wind 12 km/h.

📅  CALENDAR EVENTS
• 09:00 — Team standup (30 min)
• 14:00 — Client call with Acme Corp (1 hr)
• 17:00 — Design review (45 min)

✅  TASKS FOR THE DAY
1. [pending]  Finish the report  — due today
2. [pending]  Review pull requests  — due 2025-01-18
3. [pending]  Prepare presentation slides  — due tomorrow

💡  AI RECOMMENDATIONS
• Block 10:00–13:00 for deep work on the report — your calendar is clear.
• Prepare the client call agenda before 13:30.
• The presentation slides are due tomorrow — consider a 30-min session after 17:45.
```

---

### `GET /health` — Liveness probe

```bash
curl http://localhost:8080/health
# {"status": "ok", "service": "NeuroFlow AI", "model": "gemini-2.5-flash"}
```

### `GET /tasks` — Direct DB query (bypass agent)

```bash
curl "http://localhost:8080/tasks?status=pending"
```

### `GET /notes` — Direct DB query (bypass agent)

```bash
curl "http://localhost:8080/notes?limit=5"
```

---

## Cloud Run Deployment

### 1. Set environment variables

```bash
export PROJECT_ID="your-gcp-project-id"
export REGION="us-central1"
export SERVICE_NAME="neuroflow-ai"
export IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
```

### 2. Build and push the container

```bash
# Authenticate Docker with GCR
gcloud auth configure-docker

# Build
docker build -t "${IMAGE}" .

# Push
docker push "${IMAGE}"
```

### 3. Deploy to Cloud Run

```bash
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --platform managed \
  --region "${REGION}" \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
  --set-env-vars "GOOGLE_CLOUD_LOCATION=${REGION}" \
  --set-env-vars "GEMINI_MODEL=gemini-2.5-flash" \
  --set-env-vars "ALLOYDB_HOST=127.0.0.1" \
  --set-env-vars "ALLOYDB_PORT=5432" \
  --set-env-vars "ALLOYDB_USER=postgres" \
  --set-env-vars "ALLOYDB_DATABASE=neuroflow" \
  --set-secrets "ALLOYDB_PASSWORD=alloydb-password:latest" \
  --set-secrets "GOOGLE_API_KEY=gemini-api-key:latest" \
  --set-secrets "OPENWEATHER_API_KEY=openweather-api-key:latest" \
  --set-env-vars "CALENDAR_MCP_URL=https://calendar-mcp-server-<hash>-uc.a.run.app/mcp"
```

> **Tip:** Use `--set-secrets` for sensitive values — they're pulled from Secret Manager at runtime.

### 4. Connect AlloyDB via Cloud SQL connector (Cloud Run)

Add the `--add-cloudsql-instances` flag and use the Unix socket path:

```bash
gcloud run deploy "${SERVICE_NAME}" \
  ... \
  --add-cloudsql-instances "${PROJECT_ID}:${REGION}:neuroflow-instance" \
  --set-env-vars "ALLOYDB_HOST=/cloudsql/${PROJECT_ID}:${REGION}:neuroflow-instance"
```

### 5. Test the deployed service

```bash
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --region "${REGION}" \
  --format "value(status.url)")

curl -X POST "${SERVICE_URL}/query" \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Plan my day tomorrow"}'
```

---

## Using the ADK Dev UI

```bash
cd adk_agent
adk web neuroflow_app
```

Opens `http://localhost:8000` — a browser-based chat UI where you can interact
with the NeuroFlowCoordinator and watch agent transfers happen in real time.

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_CLOUD_PROJECT` | ✅ | Your GCP project ID |
| `GOOGLE_CLOUD_LOCATION` | ✅ | Region e.g. `us-central1` |
| `GOOGLE_API_KEY` | local dev | Gemini API key (Cloud Run uses ADC) |
| `GEMINI_MODEL` | ✅ | e.g. `gemini-2.5-flash` |
| `ALLOYDB_HOST` | ✅ | DB host or Unix socket |
| `ALLOYDB_PORT` | ✅ | Default `5432` |
| `ALLOYDB_USER` | ✅ | Database user |
| `ALLOYDB_PASSWORD` | ✅ | Database password |
| `ALLOYDB_DATABASE` | ✅ | Database name e.g. `neuroflow` |
| `CALENDAR_MCP_URL` | ✅ | Full URL to Calendar MCP server |
| `OPENWEATHER_API_KEY` | optional | OpenWeatherMap API key |
| `WEATHER_CITY` | optional | Default city for weather |
| `PORT` | ✅ | Server port (Cloud Run sets this automatically) |

---

## Adding New Agents

1. Define a new `LlmAgent` in `adk_agent/neuroflow_app/sub_agents.py`
2. Add new `FunctionTool` functions in `adk_agent/neuroflow_app/tools.py`
3. Register the agent in `root_agent`'s `sub_agents` list in `agent.py`
4. Update the coordinator's routing instruction to mention the new intent keywords

---

## Security Notes

- Never commit `.env` — add it to `.gitignore`
- Use **Secret Manager** for all secrets in Cloud Run (`--set-secrets`)
- The Cloud Run service account needs:
  - `roles/aiplatform.user` (Vertex AI / Gemini)
  - `roles/cloudsql.client` (AlloyDB)
  - `roles/calendar.events` (via OAuth, handled by ADC)
- Tighten `allow_origins` in `CORSMiddleware` for production
