import asyncio
import logging
from datetime import datetime

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.config.settings import settings
from app.models.user_model import User
from app.services.user_service import user_service
from app.services.telegram_service import telegram_service
from app.services.redis_service import redis_service
from app.services.water_scraper import WaterScraper

logger = logging.getLogger(__name__)


class BotService:

    @staticmethod
    async def send_alert_to_user(bot: Bot, user: User, alert: dict) -> bool:
        try:
            alert_message = f"""
*{alert['title']}*

{alert['message']}
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
                user_service.update_user(user.chat_id, is_active=False)
                logger.info(f"Deactivated user {user.chat_id} - bot blocked")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending alert to {user.chat_id}: {e}", exc_info=True)
            return False

    @staticmethod
    async def check_and_send_alerts():
        logger.info("Starting scheduled water alert check...")

        try:
            bot = telegram_service.bot
            if not bot:
                logger.error("Bot not initialized, skipping alert check")
                return

            active_users = user_service.get_active_users()

            if not active_users:
                logger.info("No active users to notify")
                return

            users_by_location = {}
            for user in active_users:
                if not user.location:
                    logger.warning(f"User {user.chat_id} has no location set, skipping")
                    continue

                if user.location not in users_by_location:
                    users_by_location[user.location] = []
                users_by_location[user.location].append(user)

            if not users_by_location:
                logger.info("No users with valid locations to notify")
                return

            logger.info(f"Checking alerts for {len(users_by_location)} locations")

            scraper = WaterScraper()

            try:
                all_alerts = await scraper.get_data()
                logger.info(f"Scraped {len(all_alerts)} total water alerts")

                if not all_alerts:
                    logger.info("No water alerts found")
                    return

                for location, users in users_by_location.items():
                    logger.info(f"Filtering alerts for location: {location} ({len(users)} users)")

                    location_alerts = [alert for alert in all_alerts if location in alert.get('title', '')]

                    if not location_alerts:
                        logger.info(f"No water alerts found for {location}")
                        continue

                    logger.info(f"Found {len(location_alerts)} water alerts for {location}")

                    for user in users:
                        for alert in location_alerts:
                            alert_id = alert.get('story_id')

                            if alert_id and await redis_service.has_alert_been_sent(user.chat_id, alert_id):
                                continue

                            success = await BotService.send_alert_to_user(bot, user, alert)

                            if success:
                                if alert_id:
                                    await redis_service.mark_alert_as_sent(user.chat_id, alert_id)

                                user_service.update_user(user.chat_id, last_notified=datetime.now())

                            await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error during alert check: {e}", exc_info=True)

            logger.info("Scheduled alert check completed successfully")

        except Exception as e:
            logger.error(f"Error during scheduled alert check: {e}", exc_info=True)


bot_service = BotService()
