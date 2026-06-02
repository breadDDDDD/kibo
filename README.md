# KIBO

A FastAPI backend for Mitsubishi spare parts tracking with AI-assisted chat and direct part stock lookup.

## Overview

`SparePartAI` is designed for mechanic workshops to query Mitsubishi part availability and get conversational assistance. It combines:

- FastAPI backend with REST endpoints
- Google Gemini LLM agent for natural-language part inquiries
- Direct database stock lookup for part numbers
- Async SQLAlchemy database access, supporting Cloud SQL Auth Proxy locally and Unix socket in deployment
- Minimal frontend served from `templates/index.html`

## Key Features

- `POST /api/v1/chat/message`
  - Accepts a user message and session UUID
  - Routes queries through an LLM-driven agent or direct part lookup
  - Returns structured part details and agent telemetry
- `DELETE /api/v1/chat/session/{session_id}`
  - Clears in-memory session history for a conversation
- `GET /api/v1/parts/{product_number}/stock`
  - Direct stock lookup for a validated product number
- `GET /health`
  - Simple health check endpoint

## Requirements

- Python 3.11
- Docker (optional, for containerized development)
- Access to Google Cloud credentials for Gemini and Cloud SQL

Dependencies are listed in `requirements.txt`.

## Configuration

Settings are loaded from environment variables and optionally a `.env` file.

Important variables include:

- `APP_ENV` — `development` or `production`
- `API_PREFIX` — default is `/api/v1`
- `CORS_ORIGINS` — e.g. `http://localhost:8000,http://localhost:8080`
- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_LOCATION`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `CLOUDSQL_INSTANCE_CONNECTION_NAME`
- `CLOUDSQL_DB`
- `CLOUDSQL_USER`
- `CLOUDSQL_PASSWORD`
- `CLOUDSQL_USE_PROXY` — `true` or `false`
- `CLOUDSQL_PROXY_HOST`
- `CLOUDSQL_PROXY_PORT`

The app builds a database DSN from these values in `app/core/config.py`.

## Local Development

1. Install Python dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

2. Create a `.env` file with the required values.

3. Run the app:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

4. Open the browser:

- App frontend: `http://localhost:8080/`
- API docs (development mode): `http://localhost:8080/docs`

## Docker

### Build and run locally

```bash
docker compose up --build
```

This starts two services:

- `cloudsql-proxy` — connects to Cloud SQL using the Cloud SQL Auth Proxy
- `api` — FastAPI app on port `8000`

Set `ADC_PATH` on Windows before launching if you use local ADC credentials:

```powershell
$env:ADC_PATH="C:\Users\<YOU>\AppData\Roaming\gcloud\application_default_credentials.json"
```

### Dockerfile

The multi-stage `Dockerfile` installs dependencies into a Python venv, copies the app code, and runs Uvicorn on port `8080`.

## Project Structure

- `app/main.py` — FastAPI application factory and lifecycle management
- `app/core/` — configuration, logging, Gemini client, security utilities
- `app/api/routes/` — chat and parts endpoints
- `app/db/` — async SQLAlchemy engine and session management
- `app/schemas/` — request/response models
- `app/services/agent/` — LLM agent orchestration and tool execution
- `app/services/inventory/` — part stock database queries
- `templates/` — frontend landing page
- `static/` — static assets served by FastAPI

## API Examples

### Chat message

```bash
curl -X POST http://localhost:8080/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<uuid>","message":"Do you have Mitsubishi part 7450A951 in stock?"}'
```

### Clear session

```bash
curl -X DELETE http://localhost:8080/api/v1/chat/session/<uuid>
```

### Stock lookup

```bash
curl http://localhost:8080/api/v1/parts/7450A951/stock
```

## Notes

- Session history is stored in memory per `session_id` and persists only while the process runs.
- The agent uses a hybrid approach: direct part number lookup for exact codes, and Gemini tool calls for natural language requests.
- `docker-compose.yml` is configured for local development with hot-reload and Cloud SQL Auth Proxy support.
