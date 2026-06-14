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


## Monitoring & Observability

All application monitoring, performance tracking, and log aggregation are handled natively within the **Google Cloud Platform (GCP)** ecosystem via Cloud Logging and Cloud Monitoring using **Log-based Metrics**.

To populate these metrics, the FastAPI backend emits structured JSON logs to `stdout`. Below are the configurations for tracking system performance, LLM token costs, and agent routing logic.

---

### 1. Request Latency Metric
This distribution metric tracks the execution duration of API routes and agent workflows to monitor response times and alert on bottlenecks.

* **Metric Type:** Distribution
* **Log Metric Name:** `kibo/backend/request_latency`
* **Unit:** `ms`
* **Filter Selection:**
  ```query
  resource.type="cloud_run_revision" OR resource.type="k8s_container"
  jsonPayload.message="Request processed"
  jsonPayload.duration_ms=~".*"
  ```
* **Field Name:** `jsonPayload.duration_ms`
* **Advanced Bucket Classifier:** Explicit
* **Bounds:** `100, 200, 500, 1000, 2000, 3000, 5000, 10000`

---

### 2. LLM Token Usage Metric
This counter metric extracts and aggregates the total volume of input and output tokens consumed by the Gemini API to monitor and forecast costs.

* **Metric Type:** Counter
* **Log Metric Name:** `kibo/gemini/token_usage`
* **Filter Selection:**
  ```query
  resource.type="cloud_run_revision" OR resource.type="k8s_container"
  jsonPayload.event="gemini_completion"
  jsonPayload.telemetry.total_tokens=~".*"
  ```
* **Metric Value Field:** `jsonPayload.telemetry.total_tokens` *(Ensures Cloud Logging calculates the sum of tokens rather than log row count)*
* **Labels:**
  * **Label Key:** `model` &rarr; **Field Path:** `jsonPayload.telemetry.model`
  * **Label Key:** `session_id` &rarr; **Field Path:** `jsonPayload.session_id`

---

### 3. Query Pathway Routing Metric
This counter monitors the application's hybrid logic by measuring how many user queries are handled via a high-speed direct database lookup versus the full Gemini LLM agent loop.

* **Metric Type:** Counter
* **Log Metric Name:** `kibo/chat/pathway_routing`
* **Filter Selection:**
  ```query
  resource.type="cloud_run_revision" OR resource.type="k8s_container"
  jsonPayload.event="query_routed"
  jsonPayload.pathway=~".*"
  ```
* **Labels:**
  * **Label Key:** `pathway_type` &rarr; **Field Path:** `jsonPayload.pathway` *(Expected outputs: `direct_db_lookup` or `llm_agent`)*

---

### Expected Application Log Format
For the filters above to match successfully, ensure your `app/core/logging.py` or telemetry middleware structures logs outputting to `stdout` like this:

```json
{
  "message": "Request processed",
  "event": "gemini_completion",
  "pathway": "llm_agent",
  "duration_ms": 1420,
  "session_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "telemetry": {
    "model": "gemini-1.5-flash",
    "total_tokens": 512
  }
}
```

> [!TIP]
> Once created in **Logging > Log-based Metrics**, you can directly add these metrics to a custom Google Cloud Monitoring Dashboard or use them to set up Cloud Monitoring alert policies.

## Notes

- Session history is stored in memory per `session_id` and persists only while the process runs.
- The agent uses a hybrid approach: direct part number lookup for exact codes, and Gemini tool calls for natural language requests.
- `docker-compose.yml` is configured for local development with hot-reload and Cloud SQL Auth Proxy support.
