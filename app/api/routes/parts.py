"""
Parts route — GET /api/v1/parts/{product_number}/stock
Lightweight direct stock check without the agent loop.
"""
import logging

from fastapi import APIRouter, HTTPException

from app.services.inventory.queries import get_stock_by_part_number

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/parts", tags=["parts"])


@router.get("/{product_number}/stock")
async def get_part_stock(product_number: str) -> dict:
    part = await get_stock_by_part_number(product_number)
    if part is None:
        raise HTTPException(status_code=404, detail=f"Part '{product_number}' not found")
    return {
        "product_number": part.product_number,
        "car_type": part.car_type,
        "stock": part.stock,
    }
