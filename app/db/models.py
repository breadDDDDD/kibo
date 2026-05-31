"""
ORM models — maps to the existing Cloud SQL stock_master table.
Schema mirrors the CSV: product_number (PK), car_type, stock.
"""
from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class StockMaster(Base):
    """
    master table name
    """
    __tablename__ = "mitsubishi_parts_stock"

    product_number: Mapped[str] = mapped_column(String(32), primary_key=True)
    car_type: Mapped[str] = mapped_column(String(64), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
