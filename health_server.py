import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI
import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from main import on_startup, on_shutdown

logger = logging.getLogger(__name__)


bot_state: dict = {
    "scheduler": None,
    "is_healthy": False,
    "polling_task": None
}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Starting health server and bot...")
    scheduler: Optional[AsyncIOScheduler] = None
    polling_task = None
    try:
        scheduler = await on_startup()
        bot_state["scheduler"] = scheduler

        polling_task = asyncio.create_task(start_bot_polling())
        bot_state["polling_task"] = polling_task

        bot_state["is_healthy"] = True
        logger.info("Bot started successfully, health server ready")
        yield
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)
        bot_state["is_healthy"] = False
        yield
    finally:
        logger.info("Shutting down bot...")

        if polling_task and not polling_task.done():
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                logger.info("Polling task cancelled")

        if scheduler is not None:
            await on_shutdown(scheduler)


app = FastAPI(
    title="Water Alert Bot Health Server",
    description="Health check endpoint for Koyeb deployment",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    return {
        "service": "Water Alert Bot",
        "status": "running" if bot_state["is_healthy"] else "unhealthy"
    }


@app.get("/health")
async def health_check():
    scheduler: Optional[AsyncIOScheduler] = bot_state["scheduler"]
    is_bot_running = scheduler is not None and scheduler.running if scheduler else False

    return {
        "status": "healthy" if bot_state["is_healthy"] else "unhealthy",
        "bot_running": is_bot_running
    }


@app.get("/ready")
async def readiness_check():
    return {
        "ready": bot_state["is_healthy"] and bot_state["scheduler"] is not None
    }


async def start_bot_polling():
    from app.services.telegram_service import telegram_service
    from app.config.settings import settings

    bot, dispatcher = await telegram_service.get_session()

    logger.info("Starting bot polling in background...")
    await dispatcher.start_polling(
        bot,
        polling_timeout=settings.TELEGRAM_POLLING_TIMEOUT,
        handle_signals=False,
    )


def main():
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    uvicorn.run(
        "health_server:app",
        host=host,
        port=port,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        access_log=True,
        reload=False,
        workers=1
    )


if __name__ == "__main__":
    main()
