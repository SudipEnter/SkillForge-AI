"""
SkillForge AI — FastAPI Application
Main application entry point with route registration, middleware, and startup events.
"""

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from src.config import settings
from src.api.routes import coaching, skills, learning, jobs
from src.api.websocket import router as ws_router
from src.database.dynamodb import DynamoDBClient
from src.services.skills_graph import SkillsGraphService

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    # Startup
    logger.info("SkillForge AI starting up...", environment=settings.app_env)

    # Initialize DynamoDB tables
    db = DynamoDBClient()
    await db.ensure_tables_exist()
    logger.info("DynamoDB tables verified")

    # Pre-warm the skills graph (loads role → skills mappings)
    skills_graph = SkillsGraphService()
    await skills_graph.initialize()
    logger.info("Skills knowledge graph initialized")

    logger.info(
        "SkillForge AI ready",
        nova_sonic=settings.nova_sonic_model_id,
        nova_lite=settings.nova_lite_model_id,
        nova_embeddings=settings.nova_embed_model_id,
    )

    yield

    # Shutdown
    logger.info("SkillForge AI shutting down...")


def create_app() -> FastAPI:
    app = FastAPI(
        title="SkillForge AI",
        description=(
            "Autonomous Workforce Reskilling & Career Intelligence Engine. "
            "Powered by Amazon Nova 2 Sonic, Nova 2 Lite, "
            "Nova Multimodal Embeddings, and Nova Act."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Routes
    app.include_router(ws_router, prefix="/ws", tags=["WebSocket Voice"])
    app.include_router(coaching.router, prefix="/api/v1/coaching", tags=["Coaching"])
    app.include_router(skills.router, prefix="/api/v1/skills", tags=["Skills"])
    app.include_router(learning.router, prefix="/api/v1/learning", tags=["Learning"])
    app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["Jobs"])

    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "service": "SkillForge AI",
            "version": "1.0.0",
            "nova_models": {
                "sonic": settings.nova_sonic_model_id,
                "lite": settings.nova_lite_model_id,
                "embeddings": settings.nova_embed_model_id,
            },
        }

    return app


app = create_app()