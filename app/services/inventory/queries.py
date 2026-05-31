"""
Inventory queries — async Cloud SQL lookups against stock_master.
"""
import logging

from sqlalchemy import select, func

from app.db.engine import get_session
from app.db.models import StockMaster

logger = logging.getLogger(__name__)


async def get_stock_by_part_number(product_number: str) -> StockMaster | None:
    """
    Fetches a single StockMaster row by product_number (case-insensitive).
    Returns None if not found.
    """
    async with get_session() as session:
        result = await session.execute(
            select(StockMaster).where(
                func.upper(StockMaster.product_number) == product_number.upper().strip()
            )
        )
        return result.scalar_one_or_none()


async def search_parts_by_car_type(car_type: str) -> list[StockMaster]:
    """Returns all parts for a given car model — useful for listing."""
    async with get_session() as session:
        result = await session.execute(
            select(StockMaster).where(
                func.upper(StockMaster.car_type) == car_type.upper().strip()
            )
        )
        return list(result.scalars().all())
