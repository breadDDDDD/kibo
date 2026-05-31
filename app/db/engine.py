"""
Database engine — async SQLAlchemy pool.
Supports Cloud SQL Auth Proxy (local/dev) and Unix socket (Cloud Run).
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_engine = None
_session_factory = None


def _build_engine():
    settings = get_settings()
    return create_async_engine(
        settings.db_dsn,
        pool_size=settings.db_pool_min,
        max_overflow=settings.db_pool_max - settings.db_pool_min,
        pool_pre_ping=True,
        pool_recycle=1800,
        echo=settings.is_dev,
    )


def init_db() -> None:
    global _engine, _session_factory
    _engine = _build_engine()
    _session_factory = async_sessionmaker(
        _engine, class_=AsyncSession, expire_on_commit=False
    )
    logger.info("Database engine initialised")


async def close_db() -> None:
    global _engine
    if _engine:
        await _engine.dispose()
        logger.info("Database engine disposed")


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if _session_factory is None:
        raise RuntimeError("Database not initialised — call init_db() first")
    async with _session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
