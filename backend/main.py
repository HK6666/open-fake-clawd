"""Main application entry point."""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from backend.config import settings
from backend.api.routes import router as api_router
from backend.bot.handlers import create_bot_application
from backend.claude.runner import runner_manager
from backend.memory.manager import memory_manager
from backend.db.models import db

# Shutdown event
shutdown_event = asyncio.Event()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Global bot application reference
bot_app = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global bot_app

    logger.info("Starting ccBot...")

    # Initialize settings directories
    settings.ensure_directories()

    # Initialize database
    await db.connect()
    logger.info("Database connected")

    # Initialize memory manager
    await memory_manager.initialize()
    logger.info("Memory manager initialized")

    # Create and start Telegram bot
    bot_app = create_bot_application()

    # Start bot polling in background
    await bot_app.initialize()
    await bot_app.start()
    asyncio.create_task(bot_app.updater.start_polling(drop_pending_updates=True))
    logger.info("Telegram bot started")

    # Start runner cleanup task
    await runner_manager.start_cleanup_task()
    logger.info("Runner cleanup task started")

    yield

    # Cleanup
    logger.info("Shutting down...")

    # Stop bot
    if bot_app:
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()

    # Stop cleanup task
    await runner_manager.stop_cleanup_task()

    # Stop all runners
    await runner_manager.stop_all()

    # Close database
    await db.close()

    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="ccBot",
    description="Telegram bot for Claude Code control",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)

# Serve frontend static files (if built)
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "ccBot",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs"
    }


def main():
    """Main entry point."""
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()
