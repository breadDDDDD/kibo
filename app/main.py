"""
SparePartAI — FastAPI application factory.
Handles lifespan (DB init/teardown), middleware, and route registration.
Also serves the frontend index.html at GET /.
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.engine import close_db, init_db
from app.api.routes import chat, parts
from fastapi.staticfiles import StaticFiles

CURRENT_DIR = Path(__file__).resolve().parent
setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SparePartAI starting up [env=%s]", settings.app_env)
    init_db()
    yield
    await close_db()
    logger.info("SparePartAI shut down cleanly")


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    _app = FastAPI(
        title="SparePartAI",
        version="1.0.0",
        description="AI-driven Mitsubishi spare parts tracker for mechanic workshops",
        lifespan=lifespan,
        docs_url="/docs" if settings.is_dev else None,
        redoc_url=None,
    )

    # CORS — allow the frontend origin(s)
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    static_path = CURRENT_DIR / "static"
    _app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    # API routes
    _app.include_router(chat.router, prefix=settings.api_prefix)
    _app.include_router(parts.router, prefix=settings.api_prefix)

    # Serve frontend — templates/index.html at GET /
    templates_dir = Path(__file__).parent.parent / "templates"

    @_app.get("/", include_in_schema=False)
    async def serve_frontend():
        return FileResponse(templates_dir / "index.html")

    # Health check
    @_app.get("/health", tags=["ops"])
    async def health():
        return {"status": "ok", "env": settings.app_env}

    return _app


app = create_app()
