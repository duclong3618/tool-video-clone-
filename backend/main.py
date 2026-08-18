# Author: DUC LONG
# Year: 2026
# Project: VideoDubAI

"""
VideoDubAI — FastAPI main application.

Chinese → Vietnamese video dubbing web service.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings, ensure_storage_dirs
from backend.api.routes import router as api_router
from backend.api.analytics import router as analytics_router
from backend.api.websocket import websocket_endpoint
from backend.models.database import create_tables

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    settings = get_settings()
    ensure_storage_dirs()
    logger.info("Starting %s", settings.APP_NAME)

    # Create database tables
    try:
        await create_tables()
        logger.info("Database tables created")
    except Exception as e:
        logger.warning("Could not create database tables: %s", e)
        logger.info("The app will still work; database features may be limited")

    yield

    logger.info("Shutting down %s", settings.APP_NAME)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        description="AI-powered Chinese → Vietnamese video dubbing",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    app.include_router(api_router, prefix="/api")
    app.include_router(analytics_router)

    # WebSocket endpoint
    app.websocket("/api/jobs/{job_id}/progress")(websocket_endpoint)

    # Health check
    @app.get("/health")
    async def health():
        return {"status": "ok", "app": settings.APP_NAME}

    return app


app = create_app()
