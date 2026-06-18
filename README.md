# KIBO

KIBO is an AI-powered chat application for workshop spare parts operations. It helps teams track stock, find the right part, and check availability from natural-language requests based on part description and car model.

If a user does not provide the car type/model, KIBO asks a follow-up question before proceeding so results stay accurate.

KIBO uses agentic AI workflows to:
- understand user requests in chat,
- search product catalogs for matching parts,
- validate and check live stock in SQL,
- return the most relevant spare part recommendation with availability.

## Core Capabilities

- Chat-first spare part assistant (`POST /api/v1/chat/message`)
- Direct stock lookup by part number (`GET /api/v1/parts/{product_number}/stock`)
- Session reset for conversations (`DELETE /api/v1/chat/session/{session_id}`)
- Health endpoint (`GET /health`)
- Hybrid routing:
  - direct DB path for explicit part-number queries,
  - agentic LLM + tool-calling path for natural-language requests.

## Tech Stack

- FastAPI
- SQLAlchemy async + `asyncpg`
- Google Gemini (`google-generativeai`)
- Vertex AI Agent Search (`google-cloud-discoveryengine`)
- PostgreSQL (Cloud SQL compatible)

## Local Deployment

### Prerequisites

- Python 3.11+
- Pip
- Docker Desktop (optional, for Compose workflow)
- Access credentials for Gemini/Google Cloud services
- Database access (Cloud SQL via proxy, or compatible PostgreSQL endpoint)

### 1) Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 2) Create `.env`

Create `kibo/.env` with at least:

```env
APP_ENV=development
LOG_LEVEL=INFO
API_PREFIX=/api/v1
CORS_ORIGINS=http://localhost:8000,http://localhost:8080

GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1

GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash
GEMINI_MAX_OUTPUT_TOKENS=2048
GEMINI_TEMPERATURE=0.2

AGENT_SEARCH_ENGINE_ID=your-engine-id
AGENT_SEARCH_LOCATION=global

CLOUDSQL_INSTANCE_CONNECTION_NAME=project:region:instance
CLOUDSQL_DB=sparepartdb
CLOUDSQL_USER=your-db-user
CLOUDSQL_PASSWORD=your-db-password
CLOUDSQL_USE_PROXY=true
CLOUDSQL_PROXY_HOST=127.0.0.1
CLOUDSQL_PROXY_PORT=5432

DB_POOL_MIN=2
DB_POOL_MAX=10

AGENT_MAX_TOOL_CALLS=4
RAG_TOP_K=10
```

Notes:
- `CORS_ORIGINS` supports comma-separated values.
- Set `CLOUDSQL_USE_PROXY=false` only when using Unix socket deployment mode.

### 3) Run locally (direct)

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

Open:
- App: `http://localhost:8080/`
- Docs (dev): `http://localhost:8080/docs`

### 4) Run with Docker Compose (optional)

From `kibo/`:

```bash
docker compose up --build
```

Services:
- `cloudsql-proxy` on `5432`
- `api` on `http://localhost:8000`

Windows ADC example:

```powershell
$env:ADC_PATH="C:\Users\<YOU>\AppData\Roaming\gcloud\application_default_credentials.json"
```

## Configuration Reference

KIBO settings are loaded from environment variables via `app/core/config.py`.

Important variables:
- `APP_ENV`: `development` or `production`
- `LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, `ERROR`
- `API_PREFIX`
- `CORS_ORIGINS`
- `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`
- `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_MAX_OUTPUT_TOKENS`, `GEMINI_TEMPERATURE`
- `AGENT_SEARCH_ENGINE_ID`, `AGENT_SEARCH_LOCATION`
- `CLOUDSQL_INSTANCE_CONNECTION_NAME`, `CLOUDSQL_DB`, `CLOUDSQL_USER`, `CLOUDSQL_PASSWORD`
- `CLOUDSQL_USE_PROXY`, `CLOUDSQL_PROXY_HOST`, `CLOUDSQL_PROXY_PORT`
- `DB_POOL_MIN`, `DB_POOL_MAX`
- `AGENT_MAX_TOOL_CALLS`, `RAG_TOP_K`

## Logging Setup

KIBO uses structured JSON logging to `stdout` from `app/core/logging.py`.

### Default behavior

- `setup_logging()` installs a root `StreamHandler` with JSON formatter.
- Log payload includes:
  - `severity`
  - `logger`
  - `message`
  - optional `json_fields` (merged at top level)
- Noisy loggers (`uvicorn.access`, `sqlalchemy.engine`) are reduced to `WARNING`.

### Enable and tune logging

1. Set level in `.env`:

```env
LOG_LEVEL=INFO
```

2. Ensure app startup calls `setup_logging()` (already wired in app startup flow).

3. Emit structured fields in code using `extra={"json_fields": {...}}`.

Example:

```python
logger.info(
    "chat_request",
    extra={
        "json_fields": {
            "type": "chat_request",
            "session_id": session_id,
            "pathway": pathway,
            "latency_ms": latency_ms,
            "total_tokens": input_tokens + output_tokens,
        }
    },
)
```

### Telemetry logs already included

`app/services/telemetry.py` emits async structured telemetry fields such as:
- `type`
- `pathway`
- `latency_ms`
- `input_tokens`
- `output_tokens`
- `total_tokens`
- `tool_calls`
- `tool_count`
- `session_id`
- `ts`

This format is ready for log-based metrics in Google Cloud Logging/Monitoring.

## Project Structure

- `app/main.py`: FastAPI app lifecycle
- `app/core/`: config, logging, Gemini client, input security
- `app/api/routes/`: chat + stock endpoints
- `app/services/agent/`: agent orchestration, prompts, tools
- `app/services/rag/`: catalog retrieval logic
- `app/services/inventory/`: SQL inventory queries
- `app/services/telemetry.py`: structured telemetry logs
- `app/db/`: ORM models and async engine
- `templates/`, `static/`: web UI assets

## API Examples

```bash
curl -X POST http://localhost:8080/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<uuid>","message":"Need front bumper for Xpander"}'
```

```bash
curl http://localhost:8080/api/v1/parts/7450A951/stock
```

```bash
curl -X DELETE http://localhost:8080/api/v1/chat/session/<uuid>
```

## Notes

- Session history is in-memory and tied to `session_id`.
- Responses are limited to Mitsubishi spare-parts scope.
- For best matching accuracy, include both part description and car model in requests.
