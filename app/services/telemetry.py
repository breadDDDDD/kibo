"""
Telemetry — emits structured JSON logs consumed by GCP Cloud Logging.
Log-based metrics are created in GCP Console (no new service account needed).
Write is fire-and-forget (asyncio.create_task) so it never blocks a response.
"""
import logging
from datetime import datetime, timezone

logger = logging.getLogger("sparepart.telemetry")


async def log_telemetry(
    session_id: str,
    pathway: str,
    latency_ms: float,
    input_tokens: int,
    output_tokens: int,
    tool_calls: list[str],
) -> None:
    """
    Emits a structured log entry that GCP Cloud Logging ingests as jsonPayload.
    Your existing JsonFormatter in logging.py already handles json_fields —
    so each key below becomes a top-level field in jsonPayload, queryable in
    Log Explorer and extractable as a log-based metric.
    """
    try:
        logger.info(
            "chat_request",  # becomes jsonPayload.message — use as log filter
            extra={
                "json_fields": {
                    "type":          "chat_request",         # filter anchor
                    "pathway":       pathway,                 # "A" | "B" | "C"
                    "latency_ms":    round(latency_ms, 2),   # graphable distribution
                    "input_tokens":  input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens":  input_tokens + output_tokens,
                    "tool_calls":    tool_calls,
                    "tool_count":    len(tool_calls),
                    "session_id":    session_id,
                    "ts":            datetime.now(timezone.utc).isoformat(),
                }
            },
        )
    except Exception as exc:
        # Telemetry must never crash the app
        logger.warning("Telemetry write failed: %s", exc)