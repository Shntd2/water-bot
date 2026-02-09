import logging
import os
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Request, Response
import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.types import Update

from main import on_startup, on_shutdown
from app.config.settings import settings

logger = logging.getLogger(__name__)


bot_state: dict = {
    "scheduler": None,
    "is_healthy": False
}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Starting health server and bot...")
    scheduler: Optional[AsyncIOScheduler] = None
    try:
        from app.services.telegram_service import telegram_service

        scheduler = await on_startup()
        bot_state["scheduler"] = scheduler

        webhook_secret = settings.TELEGRAM_WEBHOOK_SECRET if settings.TELEGRAM_WEBHOOK_SECRET else None
        webhook_setup_success = await telegram_service.setup_webhook(
            webhook_url=settings.TELEGRAM_WEBHOOK_URL,
            secret_token=webhook_secret
        )

        if webhook_setup_success:
            bot_state["is_healthy"] = True
            logger.info("Bot started successfully with webhook, health server ready")
        else:
            logger.error("Failed to setup webhook")
            bot_state["is_healthy"] = False

        yield
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)
        bot_state["is_healthy"] = False
        yield
    finally:
        logger.info("Shutting down bot...")

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


@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check(request: Request):
    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.headers.get("X-Real-IP")
        or (request.client.host if request.client else None)
    )

    if client_ip not in settings.WHITELIST_LOCATION:
        logger.warning(f"Health check denied for IP: {client_ip}")
        return Response(status_code=403)

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


@app.post(settings.TELEGRAM_WEBHOOK_PATH)
async def webhook_handler(request: Request):
    from app.services.telegram_service import telegram_service

    try:
        if settings.TELEGRAM_WEBHOOK_SECRET:
            secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if secret_header != settings.TELEGRAM_WEBHOOK_SECRET:
                logger.warning("Invalid webhook secret token")
                return Response(status_code=403)

        update_data = await request.json()

        bot, dispatcher = await telegram_service.get_session()
        update = Update(**update_data)
        await dispatcher.feed_update(bot, update)

        return Response(status_code=200)

    except Exception as e:
        logger.error(f"Error processing webhook update: {e}", exc_info=True)
        return Response(status_code=500)


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
