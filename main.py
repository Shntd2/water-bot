import asyncio
import logging
import sys
from datetime import datetime
from typing import Dict, Set

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramAPIError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config.settings import settings
from app.handlers.message_handlers import router
from app.models.telegram_models import user_db, User
from app.services.telegram_service import telegram_service
from app.services.water_scraper import WaterScraper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('water_bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

sent_alerts: Dict[int, Set[str]] = {}


async def send_alert_to_user(bot: Bot, user: User, alert: dict) -> bool:
    try:
        alert_message = f"""
💧 *New Water Alert*

*{alert['title']}*

{alert['message']}

🔗 [View the source]({alert['url']})

_Alert ID: {alert['story_id']}_
        """

        await bot.send_message(
            chat_id=user.chat_id,
            text=alert_message,
            parse_mode=settings.TELEGRAM_PARSE_MODE,
            disable_web_page_preview=True,
        )

        logger.info(f"Alert sent to user {user.chat_id} (@{user.username})")
        return True

    except TelegramAPIError as e:
        logger.error(f"Failed to send alert to user {user.chat_id}: {e}")
        if "bot was blocked" in str(e).lower():
            user_db.update_user(user.chat_id, is_active=False)
            logger.info(f"Deactivated user {user.chat_id} - bot blocked")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending alert to {user.chat_id}: {e}", exc_info=True)
        return False


async def check_and_send_alerts():
    logger.info("Starting scheduled water alert check...")

    try:
        bot = telegram_service.bot
        if not bot:
            logger.error("Bot not initialized, skipping alert check")
            return

        scraper = WaterScraper()
        alerts = scraper.get_data(location=settings.TARGET_LOCATION)

        if not alerts:
            logger.info("No water alerts found")
            return

        logger.info(f"Found {len(alerts)} water alerts")

        active_users = user_db.get_active_users()

        if not active_users:
            logger.info("No active users to notify")
            return

        logger.info(f"Sending alerts to {len(active_users)} active users")

        for user in active_users:
            if user.chat_id not in sent_alerts:
                sent_alerts[user.chat_id] = set()

            for alert in alerts:
                alert_id = alert.get('story_id')

                if alert_id and alert_id in sent_alerts[user.chat_id]:
                    continue

                success = await send_alert_to_user(bot, user, alert)

                if success:
                    if alert_id:
                        sent_alerts[user.chat_id].add(alert_id)

                    user_db.update_user(user.chat_id, last_notified=datetime.now())

                await asyncio.sleep(0.1)

        logger.info("Scheduled alert check completed successfully")

    except Exception as e:
        logger.error(f"Error during scheduled alert check: {e}", exc_info=True)


async def on_startup():
    logger.info("Starting Water Alert Bot...")

    try:
        bot, dispatcher = await telegram_service.get_session()

        dispatcher.include_router(router)

        scheduler = AsyncIOScheduler()

        scheduler.add_job(
            check_and_send_alerts,
            trigger=IntervalTrigger(minutes=1),
            id='water_alert_check',
            name='Check and send water alerts',
            replace_existing=True,
        )

        scheduler.start()
        logger.info("Scheduler started - alerts will be checked every 60 minutes")

        logger.info("Running initial water alert check...")
        await check_and_send_alerts()

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
