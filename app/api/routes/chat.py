"""
Chat routes — POST /api/v1/chat/message, DELETE /api/v1/chat/session/{session_id}
"""
import asyncio
import logging

from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.agent.agent import clear_session, run_agent
from app.services.telemetry import log_telemetry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/message", response_model=ChatResponse)
async def chat_message(payload: ChatRequest) -> ChatResponse:
    """
    Main chat endpoint. Receives a user message and returns a structured
    response including optional part data and telemetry stats.
    """
    try:
        result = await run_agent(
            session_id=payload.session_id,
            message=payload.message,
        )
    except Exception as exc:
        logger.exception("Agent error for session %s: %s", payload.session_id, exc)
        raise HTTPException(status_code=500, detail="Agent processing failed") from exc

    # Fire-and-forget telemetry write
    asyncio.create_task(
        log_telemetry(
            session_id=payload.session_id,
            pathway=result.telemetry.pathway,
            latency_ms=result.telemetry.latency_ms,
            input_tokens=result.telemetry.input_tokens,
            output_tokens=result.telemetry.output_tokens,
            tool_calls=result.telemetry.tool_calls,
        )
    )

    return ChatResponse(
        session_id=payload.session_id,
        reply=result.reply,
        part=result.part,
        telemetry=result.telemetry,
    )


@router.delete("/session/{session_id}", status_code=204)
async def clear_chat_session(session_id: str) -> None:
    """Erases all in-memory conversation history for a session."""
    clear_session(session_id)
