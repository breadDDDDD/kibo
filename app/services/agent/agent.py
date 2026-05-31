"""
Agent orchestrator — the brain of SparePartAI.

Routing logic:
  Pathway B — message matches a bare part-number pattern → skip LLM, direct DB lookup.
  Pathway A — natural description → Gemini tool-calling loop (RAG → DB).
  Pathway C — out-of-scope → LLM soft-reject, no tools executed.

Multi-turn history is maintained per session_id in-process (dict of lists).
"""
import asyncio
import logging
import re
import time
from dataclasses import dataclass, field

import google.generativeai as genai

from app.core.gemini_client import get_gemini_client
from app.core.config import get_settings
from app.schemas.chat import PartResult, TelemetryData
from app.services.agent.prompts import SYSTEM_PROMPT
from app.services.agent.tool_executor import execute_tool
from app.services.agent.tools import TOOLS
from app.services.inventory.queries import get_stock_by_part_number

logger = logging.getLogger(__name__)

# ── Part-number pattern — alphanumeric codes like 7450A951, MD360935M ──────
PART_NUMBER_RE = re.compile(r"\b([A-Z]{0,4}\d{3,6}[A-Z]\d{2,4}[A-Z]?)\b", re.IGNORECASE)

# ── In-process conversation store: session_id → list of Content objects ────
_sessions: dict[str, list] = {}


# ── Result dataclass ────────────────────────────────────────────────────────

@dataclass
class AgentResult:
    reply: str | None = None
    part: PartResult | None = None
    telemetry: TelemetryData = field(
        default_factory=lambda: TelemetryData(
            latency_ms=0, input_tokens=0, output_tokens=0, pathway="C"
        )
    )


def clear_session(session_id: str) -> None:
    """Erase all conversation history for a session."""
    _sessions.pop(session_id, None)
    logger.info("Session cleared: %s", session_id)


# ── Pathway B: direct part-number short-circuit ─────────────────────────────

async def _pathway_b(session_id: str, message: str, part_number: str) -> AgentResult:
    start = time.perf_counter()
    logger.info("[Pathway B] Direct stock lookup: %s", part_number)

    part_row = await get_stock_by_part_number(part_number)
    latency = (time.perf_counter() - start) * 1000

    if part_row is None:
        return AgentResult(
            reply=f"No part found with number **{part_number}** in the database.",
            telemetry=TelemetryData(
                latency_ms=round(latency, 2),
                input_tokens=0,
                output_tokens=0,
                tool_calls=["get_stock_by_part_id"],
                pathway="B",
            ),
        )

    return AgentResult(
        part=PartResult(
            product_number=part_row.product_number,
            car_type=part_row.car_type,
            stock=part_row.stock,
        ),
        telemetry=TelemetryData(
            latency_ms=round(latency, 2),
            input_tokens=0,
            output_tokens=0,
            tool_calls=["get_stock_by_part_id"],
            pathway="B",
        ),
    )


# ── Pathway A/C: LLM agentic loop ────────────────────────────────────────────

async def _pathway_ac(session_id: str, message: str) -> AgentResult:
    settings = get_settings()
    model = get_gemini_client()
    start = time.perf_counter()

    tool_calls_log: list[str] = []
    input_tokens = 0
    output_tokens = 0

    # Build / retrieve conversation history
    history = _sessions.get(session_id, [])

    # Append user turn
    history.append({"role": "user", "parts": [message]})

    # Agentic loop — bounded by AGENT_MAX_TOOL_CALLS
    part_result: PartResult | None = None
    final_reply: str | None = None
    pathway = "A"

    for iteration in range(settings.agent_max_tool_calls + 1):
        # Run Gemini in executor to keep async event loop free
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: model.generate_content(
                history,
                tools=[TOOLS],
                system_instruction=SYSTEM_PROMPT,
                tool_config={"function_calling_config": {"mode": "AUTO"}},
            ),
        )

        # Accumulate token usage
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            input_tokens += getattr(response.usage_metadata, "prompt_token_count", 0) or 0
            output_tokens += getattr(response.usage_metadata, "candidates_token_count", 0) or 0

        candidate = response.candidates[0]
        content = candidate.content  # Content object with .parts

        # Add model response to history
        history.append({"role": "model", "parts": content.parts})

        # Check if model wants to call tools
        tool_call_parts = [p for p in content.parts if hasattr(p, "function_call") and p.function_call.name]

        if not tool_call_parts:
            # No more tool calls — extract text reply
            text_parts = [p.text for p in content.parts if hasattr(p, "text") and p.text]
            final_reply = " ".join(text_parts).strip()

            # Detect if this was Pathway C (no tools used at all)
            if not tool_calls_log:
                pathway = "C"
            break

        # Execute each requested tool
        function_responses = []
        for part in tool_call_parts:
            fc = part.function_call
            tool_name = fc.name
            tool_args = dict(fc.args) if fc.args else {}
            tool_calls_log.append(tool_name)

            logger.info("[Pathway A] Tool call: %s(%s)", tool_name, tool_args)
            tool_result = await execute_tool(tool_name, tool_args)

            # If stock lookup succeeded, capture part data
            if tool_name == "get_stock_by_part_id" and tool_result.get("found"):
                part_result = PartResult(
                    product_number=tool_result["product_number"],
                    car_type=tool_result["car_type"],
                    stock=tool_result["stock"],
                )

            function_responses.append(
                genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=tool_name,
                        response={"result": tool_result},
                    )
                )
            )

        # Add tool results back to history
        history.append({"role": "user", "parts": function_responses})

    # Persist updated history
    _sessions[session_id] = history

    latency = (time.perf_counter() - start) * 1000

    return AgentResult(
        reply=final_reply if not part_result else None,
        part=part_result,
        telemetry=TelemetryData(
            latency_ms=round(latency, 2),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            tool_calls=tool_calls_log,
            pathway=pathway,
        ),
    )


# ── Public entry point ────────────────────────────────────────────────────────

async def run_agent(session_id: str, message: str) -> AgentResult:
    """
    Main entry point. Routes to the correct pathway based on message content.
    """
    # Pathway B check: does the message contain an explicit part number?
    match = PART_NUMBER_RE.search(message)
    if match:
        logger.info("[Router] Pathway B detected, part number: %s", match.group(1))
        return await _pathway_b(session_id, message, match.group(1))

    # Pathway A/C: send to LLM
    return await _pathway_ac(session_id, message)
