from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.health import router as health_router
from backend.app.core.config import settings
from backend.app.core.logging import setup_logging

logger = logging.getLogger("sovereign_workbench.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    logger.info(f"Starting {settings.app.name} v{settings.app.version} in {settings.app.environment} mode")
    # Ensure data directory exists
    root = settings.paths.data_dir
    root.mkdir(parents=True, exist_ok=True)
    yield
    logger.info(f"Shutting down {settings.app.name}")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app.name,
        version=settings.app.version,
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health router
    app.include_router(health_router)

    return app


app = create_app()
