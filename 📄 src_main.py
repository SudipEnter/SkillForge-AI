"""
SkillForge AI — FastAPI Application Entry Point
Amazon Nova AI Hackathon | Agentic AI + Voice AI + Multimodal + UI Automation
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import settings
from src.api.routes import coaching, health, jobs, learning, skills
from src.api.websocket import router as ws_router

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle — startup diagnostics + shutdown cleanup."""
    logger.info("━" * 60)
    logger.info("🚀  SkillForge AI — Amazon Nova AI Hackathon")
    logger.info("━" * 60)
    logger.info(f"   Region        : {settings.bedrock_region}")
    logger.info(f"   Nova 2 Lite   : {settings.nova2_lite_model_id}")
    logger.info(f"   Nova 2 Sonic  : {settings.nova2_sonic_model_id}")
    logger.info(f"   Nova Embed    : {settings.nova_embeddings_model_id}")
    logger.info(f"   Nova Act      : {'✅ enabled' if settings.nova_act_api_key else '⚠️  no key'}")
    logger.info(f"   Environment   : {settings.environment}")
    logger.info("━" * 60)
    yield
    logger.info("👋  SkillForge AI shutdown complete")


app = FastAPI(
    title="SkillForge AI",
    description=(
        "Autonomous Workforce Reskilling Engine powered by Amazon Nova.\n\n"
        "**Nova Models Used:**\n"
        "- **Nova 2 Sonic** — Real-time voice career coaching\n"
        "- **Nova 2 Lite** — Multi-agent reasoning & skills gap analysis\n"
        "- **Nova Embeddings** — Multimodal skills/portfolio matching\n"
        "- **Nova Act** — Autonomous web-based course enrollment\n\n"
        "Built for the Amazon Nova AI Hackathon 2025."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(coaching.router, prefix="/api/v1/coaching", tags=["Voice Coaching"])
app.include_router(skills.router,   prefix="/api/v1/skills",   tags=["Skills Analysis"])
app.include_router(learning.router, prefix="/api/v1/learning", tags=["Learning Paths"])
app.include_router(jobs.router,     prefix="/api/v1/jobs",     tags=["Job Market"])
app.include_router(ws_router,       prefix="/ws",              tags=["WebSocket"])


# ── Error Handlers ─────────────────────────────────────────────────────
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def generic_error_handler(request, exc):
    logger.exception(f"Unhandled error on {request.url}: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


def main():
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
        access_log=True,
    )


if __name__ == "__main__":
    main()