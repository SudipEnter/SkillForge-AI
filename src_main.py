"""
SkillForge AI — Application Entry Point
Launches the FastAPI server with Uvicorn for development and production.
"""

import uvicorn
from src.config import settings


def main():
    uvicorn.run(
        "src.api.app:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
        ws_ping_interval=30,
        ws_ping_timeout=60,
        access_log=True,
    )


if __name__ == "__main__":
    main()