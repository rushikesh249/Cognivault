from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Explicitly disable ChromaDB telemetry
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from backend.app.api.health import router as health_router
from backend.app.api.models import router as models_router, get_model_registry
from backend.app.api.tasks import router as tasks_router
from backend.app.api.knowledge import router as knowledge_router
from backend.app.api.code import router as code_router
from backend.app.api.agent import router as agent_router
from backend.app.api.events import router as events_router
from backend.app.core.config import settings
from backend.app.core.logging import setup_logging
from backend.app.persistence.db import init_db

logger = logging.getLogger("sovereign_workbench.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    logger.info(f"Starting {settings.app.name} v{settings.app.version} in {settings.app.environment} mode")
    
    # Ensure data and sandbox directories exist
    root = settings.paths.data_dir
    root.mkdir(parents=True, exist_ok=True)
    Path(settings.rag.chroma.persist_directory).mkdir(parents=True, exist_ok=True)
    (root / "sandbox").mkdir(parents=True, exist_ok=True)
    
    # Initialize SQLite database schema
    init_db()
    
    # Initialize / validate Model Registry
    registry = get_model_registry()
    logger.info(f"Initialized Model Registry with {registry.count()} configured models")
    
    yield
    logger.info(f"Shutting down {settings.app.name}")


def create_app() -> FastAPI:
    app_instance = FastAPI(
        title=settings.app.name,
        version=settings.app.version,
        lifespan=lifespan,
    )

    # CORS configuration
    app_instance.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API routers
    app_instance.include_router(health_router)
    app_instance.include_router(models_router)
    app_instance.include_router(tasks_router)
    app_instance.include_router(knowledge_router)
    app_instance.include_router(code_router)
    app_instance.include_router(agent_router)
    app_instance.include_router(events_router)

    return app_instance


app = create_app()
