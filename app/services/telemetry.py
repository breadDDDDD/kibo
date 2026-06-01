# """
# Telemetry — appends each request's stats to telemetry/telemetry.json.
# Write is fire-and-forget (asyncio.create_task) so it never blocks a response.
# """
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

# logger = logging.getLogger(__name__)
logger = logging.getLogger("sparepart.telemetry")

# TELEMETRY_PATH = Path("telemetry/telemetry.json")


# def _write_entry(entry: dict) -> None:
#     """Synchronous append — runs in a thread executor."""
#     TELEMETRY_PATH.parent.mkdir(parents=True, exist_ok=True)
#     # Read existing list, append, rewrite — keeps it a valid JSON array.
#     data: list[dict] = []
#     if TELEMETRY_PATH.exists() and TELEMETRY_PATH.stat().st_size > 0:
#         try:
#             with open(TELEMETRY_PATH) as f:
#                 data = json.load(f)
#         except (json.JSONDecodeError, OSError):
#             data = []
#     data.append(entry)
#     with open(TELEMETRY_PATH, "w") as f:
#         json.dump(data, f, indent=2)


# async def log_telemetry(
#     session_id: str,
#     pathway: str,
#     latency_ms: float,
#     input_tokens: int,
#     output_tokens: int,
#     tool_calls: list[str],
# ) -> None:
#     """Fire-and-forget telemetry write — called with asyncio.create_task."""
#     entry = {
#         "ts": datetime.now(timezone.utc).isoformat(),
#         "session_id": session_id,
#         "pathway": pathway,
#         "latency_ms": round(latency_ms, 2),
#         "input_tokens": input_tokens,
#         "output_tokens": output_tokens,
#         "tool_calls": tool_calls,
#     }
#     loop = asyncio.get_event_loop()
#     try:
#         await loop.run_in_executor(None, _write_entry, entry)
#     except Exception as exc:  # telemetry must never crash the app
#         logger.warning("Telemetry write failed: %s", exc)


logger = logging.getLogger("sparepart.telemetry")


async def log_telemetry(
    session_id: str,
    pathway: str,
    latency_ms: float,
    input_tokens: int,
    output_tokens: int,
    tool_calls: list[str],
) -> None:
    try:
        logger.info(
            "chat_request latency=%.2f tokens=%d pathway=%s",
            latency_ms,
            input_tokens + output_tokens,
            pathway,
        )
    except Exception as exc:
        logger.warning("Telemetry write failed: %s", exc)
