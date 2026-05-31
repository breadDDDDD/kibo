# ══════════════════════════════════════════════════════════════════════
#  SparePartAI — Multi-stage Dockerfile
#  Stage 1: install deps into a venv
#  Stage 2: copy venv + app source into a minimal runtime image
# ══════════════════════════════════════════════════════════════════════

# ── Stage 1: dependency builder ────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# System deps needed to compile some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create isolated venv
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefer-binary --index-url https://pypi.org/simple -r requirements.txt


# ── Stage 2: runtime image ─────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Runtime system deps (libpq for asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN groupadd --gid 1000 appuser && useradd --uid 1000 --gid appuser appuser

WORKDIR /app

# Copy venv from builder
COPY --from=builder /venv /venv
ENV PATH="/venv/bin:$PATH"

# Copy application source
COPY app/ ./app/
COPY templates/ ./templates/

# Telemetry directory — writable by appuser
RUN mkdir -p /app/telemetry && chown appuser:appuser /app/telemetry

USER appuser

# Cloud Run listens on 8080
EXPOSE 8080

# Single worker — scale via Cloud Run instances, not threads
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
