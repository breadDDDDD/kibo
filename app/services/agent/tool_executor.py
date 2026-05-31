"""
Tool executor — runs the actual implementation for each tool call
the Gemini model requests. Returns structured dicts as tool results.
"""
import logging
from typing import Any

from app.services.inventory.queries import get_stock_by_part_number
from app.services.rag.vertex_search import (
    format_chunks_for_prompt,
    search_parts_catalog,
)

logger = logging.getLogger(__name__)


async def execute_tool(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """
    Dispatches to the correct implementation and returns a result dict
    that will be sent back to Gemini as a function response.
    """
    if tool_name == "search_parts_catalog":
        return await _run_rag_search(args)

    if tool_name == "get_stock_by_part_id":
        return await _run_stock_lookup(args)

    logger.warning("Unknown tool requested: %s", tool_name)
    return {"error": f"Unknown tool: {tool_name}"}


async def _run_rag_search(args: dict) -> dict:
    query = args.get("query", "")
    logger.info("RAG search: %s", query)
    chunks = await search_parts_catalog(query)
    formatted = format_chunks_for_prompt(chunks)
    return {
        "catalog_context": formatted,
        "chunk_count": len(chunks),
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
