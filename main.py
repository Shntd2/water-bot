import asyncio
import logging
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config.settings import settings
from app.handlers.message_handlers import router
from app.services.telegram_service import telegram_service
from app.services.redis_service import redis_service
from app.services.bot_service import bot_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('water_bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


async def on_startup():
    logger.info("Starting Water Alert Bot...")

    try:
        await redis_service.connect()

        bot, dispatcher = await telegram_service.get_session()

        dispatcher.include_router(router)

        scheduler = AsyncIOScheduler()

        scheduler.add_job(
            bot_service.check_and_send_alerts,
            trigger=IntervalTrigger(minutes=60),
            id='water_alert_check',
            name='Check and send water alerts',
            replace_existing=True,
        )

        scheduler.start()
        logger.info("Scheduler started - alerts will be checked every 60 minutes")

        logger.info("Running initial water alert check...")
        await bot_service.check_and_send_alerts()

        logger.info("Bot startup completed successfully")

        return scheduler

    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)
        raise


async def on_shutdown(scheduler: AsyncIOScheduler):
    logger.info("Shutting down Water Alert Bot...")

    try:
        if scheduler and scheduler.running:
            scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

        await telegram_service.close_session()

        await redis_service.close()

        logger.info("Bot shutdown completed")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)


async def main():
    scheduler = None

    try:
        scheduler = await on_startup()

        bot, dispatcher = await telegram_service.get_session()

        logger.info("Starting bot polling...")
        await dispatcher.start_polling(
            bot,
            polling_timeout=settings.TELEGRAM_POLLING_TIMEOUT,
            handle_signals=True,
        )

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error in main loop: {e}", exc_info=True)
    finally:
        await on_shutdown(scheduler)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
