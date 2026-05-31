"""
Logging — JSON in production, coloured pretty-print in development.
Call `setup_logging()` once at app startup.
"""
import logging
import sys

from app.core.config import get_settings


def setup_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    if settings.is_dev:
        fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        logging.basicConfig(level=level, format=fmt, stream=sys.stdout)
    else:
        # Minimal JSON-style for Cloud Logging ingestion
        import json

        class JsonFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:  # noqa: A003
                payload = {
                    "severity": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }
                if record.exc_info:
                    payload["exc_info"] = self.formatException(record.exc_info)
                return json.dumps(payload)

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        root = logging.getLogger()
        root.setLevel(level)
        root.addHandler(handler)

    # Silence noisy third-party loggers
    for noisy in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
