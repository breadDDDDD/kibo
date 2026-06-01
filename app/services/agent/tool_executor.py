"""
Tool executor — runs the actual implementation for each tool call
the Gemini model requests. Returns structured dicts as tool results.

Car type is enforced at TWO layers:
  1. The search query always includes the car model (better RAG ranking)
  2. Returned chunks are post-filtered — any chunk that doesn't mention
     the requested car model is discarded before the model sees it.
"""
import logging
from typing import Any

from app.services.inventory.queries import get_stock_by_part_number
from app.services.rag.vertex_search import (
    format_chunks_for_prompt,
    search_parts_catalog,
)

logger = logging.getLogger(__name__)

# Known car models — used for chunk filtering
CAR_MODELS = ["xpander", "pajero sport", "pajero", "xforce", "x-force", "destinator"]


def _filter_chunks_by_car(chunks: list[dict], car_model: str) -> list[dict]:
    """
    Discard any chunk that doesn't mention the requested car model.
    Case-insensitive. Returns all chunks if car_model is empty/unknown.
    """
    if not car_model:
        return chunks

    car_lower = car_model.lower()
    filtered = [
        c for c in chunks
        if car_lower in c["content"].lower()
    ]

    if not filtered:
        logger.warning(
            "Car filter '%s' removed all %d chunks — returning unfiltered as fallback",
            car_model, len(chunks)
        )
        # Return empty so the model knows nothing matched — don't silently fall back
        return []

    logger.info(
        "Car filter '%s': %d/%d chunks passed", car_model, len(filtered), len(chunks)
    )
    return filtered


async def execute_tool(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    if tool_name == "search_parts_catalog":
        return await _run_rag_search(args)
    if tool_name == "get_stock_by_part_id":
        return await _run_stock_lookup(args)
    logger.warning("Unknown tool requested: %s", tool_name)
    return {"error": f"Unknown tool: {tool_name}"}


async def _run_rag_search(args: dict) -> dict:
    query     = args.get("query", "")
    car_model = args.get("car_model", "").strip()

    # Always include car model in the search query for better ranking
    search_query = f"{query} {car_model}".strip() if car_model else query
    logger.info("RAG search: %s (car_model=%s)", search_query, car_model or "unspecified")

    chunks = await search_parts_catalog(search_query)

    # Hard filter — discard chunks that don't mention the requested car
    if car_model:
        chunks = _filter_chunks_by_car(chunks, car_model)

    if not chunks:
        return {
            "catalog_context": f"No catalog entries found for '{query}' matching car model '{car_model}'.",
            "chunk_count": 0,
            "car_model_filter": car_model,
        }

    formatted = format_chunks_for_prompt(chunks)
    return {
        "catalog_context": formatted,
        "chunk_count": len(chunks),
        "car_model_filter": car_model,
    }


async def _run_stock_lookup(args: dict) -> dict:
    product_number = args.get("product_number", "").strip()
    logger.info("Stock lookup: %s", product_number)
    part = await get_stock_by_part_number(product_number)

    if part is None:
        return {
            "found": False,
            "product_number": product_number,
            "message": f"No part found with number: {product_number}",
        }

    return {
        "found": True,
        "product_number": part.product_number,
        "car_type": part.car_type,
        "stock": part.stock,
    }