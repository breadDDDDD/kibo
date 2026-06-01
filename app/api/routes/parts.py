"""
Parts route — GET /api/v1/parts/{product_number}/stock
Lightweight direct stock check without the agent loop.
"""
import logging
import re

from fastapi import APIRouter, HTTPException

from app.services.inventory.queries import get_stock_by_part_number

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/parts", tags=["parts"])

_PART_NUMBER_RE = re.compile(r"^[A-Z0-9]{4,16}$", re.IGNORECASE)

@router.get("/{product_number}/stock")
async def get_part_stock(product_number: str) -> dict:
    if not _PART_NUMBER_RE.match(product_number):
        raise HTTPException(status_code=400, detail="Invalid product number format.")
    part = await get_stock_by_part_number(product_number)
    if part is None:
        raise HTTPException(status_code=404, detail=f"Part '{product_number}' not found")
    return {
        "product_number": part.product_number,
        "car_type": part.car_type,
        "stock": part.stock,
    }
