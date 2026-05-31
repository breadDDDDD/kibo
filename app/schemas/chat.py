"""
Pydantic v2 schemas — request/response contracts for the chat API.
"""
from typing import Any

from pydantic import BaseModel, Field


# ── Request ────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(..., description="Client-generated UUID for this conversation")


# ── Sub-models ─────────────────────────────────────────────────────────────

class PartResult(BaseModel):
    product_number: str
    car_type: str
    stock: int
    part_name: str | None = None      # from RAG chunk
    description: str | None = None    # from RAG chunk


class TelemetryData(BaseModel):
    latency_ms: float
    input_tokens: int
    output_tokens: int
    tool_calls: list[str] = Field(default_factory=list)
    pathway: str = Field(description="A | B | C")


# ── Response ───────────────────────────────────────────────────────────────

class ChatResponse(BaseModel):
    session_id: str
    reply: str | None = Field(None, description="Text reply (Pathway C or error)")
    part: PartResult | None = Field(None, description="Populated on Pathway A/B match")
    telemetry: TelemetryData
