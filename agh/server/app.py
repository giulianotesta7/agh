"""FastAPI application factory and health endpoint."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI

DEFAULT_PORT = 8912

_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
_LOGGING_CONFIGURED = False
_HANDLER_MARKER = "_agh_managed_handler"


def get_data_dir() -> Path:
    """Return the AGH data directory.

    Local development defaults to a writable repo-local directory. The Docker
    image sets ``AGH_DATA_DIR=/data`` so self-hosted deployments use the
    container volume layout from the SDD design.
    """
    return Path(os.environ.get("AGH_DATA_DIR", ".agh-data"))


def configure_logging() -> Path:
    """Configure stdout and file logging; idempotent across repeated calls."""
    global _LOGGING_CONFIGURED

    data_dir = get_data_dir()
    log_dir = data_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "agh.log"
    log_path.touch(exist_ok=True)

    logger = logging.getLogger("agh")
    logger.setLevel(logging.INFO)

    existing_handlers = [
        handler
        for handler in logger.handlers
        if getattr(handler, _HANDLER_MARKER, False)
    ]
    if _LOGGING_CONFIGURED and existing_handlers:
        return log_path

    for handler in existing_handlers:
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(_LOG_FORMAT)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    setattr(stream_handler, _HANDLER_MARKER, True)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    setattr(file_handler, _HANDLER_MARKER, True)
    logger.addHandler(file_handler)

    logger.propagate = False
    _LOGGING_CONFIGURED = True
    logger.info("AGH logging initialized at %s", log_path)
    return log_path


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    configure_logging()

    application = FastAPI(title="Agent Guidance Hub", version="0.1.0")

    @application.get("/api/v1/health")
    def health() -> dict[str, str | int]:
        return {"status": "ok", "port": DEFAULT_PORT}

    return application


app = create_app()
