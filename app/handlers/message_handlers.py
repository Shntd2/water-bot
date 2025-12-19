import logging
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from datetime import datetime

from app.models.telegram_models import User, user_db
from app.services.water_scraper import WaterScraper

from app.config.settings import settings

logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    chat_id = message.chat.id
    user = user_db.get_user(chat_id)

    welcome_text = """
🛠️ *Welcome to Water Alert Bot!*

This bot monitors water supply alerts for Yerevan and sends you notifications.

*Available Commands:*
/subscribe - Subscribe to water alerts
/unsubscribe - Unsubscribe from alerts
/status - Check your subscription status
/check - Check current water alerts
/help - Show this help message

You'll receive notifications when new water supply information is available.
    """

    if not user:
        new_user = User(
            chat_id=chat_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            location=settings.TARGET_LOCATION,
            subscribed_at=datetime.now(),
            is_active=True,
        )
        user_db.add_user(new_user)
        logger.info(f"New user subscribed: {chat_id} (@{message.from_user.username})")

    await message.answer(welcome_text, parse_mode="Markdown")


@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = """
🛠️ *Water Alert Bot Help*

*Available Commands:*
/start - Start the bot and subscribe
/subscribe - Subscribe to water alerts
/unsubscribe - Unsubscribe from alerts
/status - Check your subscription status
/check - Check current water alerts
/help - Show this help message

*About:*
This bot monitors water supply stats and sends you notifications when new alerts are posted for your area
    """
    await message.answer(help_text, parse_mode="Markdown")


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message):
    chat_id = message.chat.id
    user = user_db.get_user(chat_id)

    if user:
        if user.is_active:
            await message.answer(
                "✅ You are already subscribed to water alerts!\n\n"
                f"Location: *{user.location}*\n"
                f"Subscribed since: {user.subscribed_at.strftime('%Y-%m-%d %H:%M')}",
                parse_mode="Markdown"
            )
        else:
            user_db.update_user(chat_id, is_active=True)
            await message.answer(
                "✅ *Subscription reactivated!*\n\n"
                "You will now receive water alerts again.",
                parse_mode="Markdown"
            )
            logger.info(f"User resubscribed: {chat_id}")
    else:
        new_user = User(
            chat_id=chat_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            location=settings.TARGET_LOCATION,
            subscribed_at=datetime.now(),
            is_active=True,
        )
        user_db.add_user(new_user)
        await message.answer(
            "✅ *Successfully subscribed!*\n\n"
            f"You will receive water alerts for: *{new_user.location}*",
            parse_mode="Markdown"
        )
        logger.info(f"User subscribed: {chat_id} (@{message.from_user.username})")


@router.message(Command("unsubscribe"))
async def cmd_unsubscribe(message: Message):
    chat_id = message.chat.id
    user = user_db.get_user(chat_id)

    if user and user.is_active:
        user_db.update_user(chat_id, is_active=False)
        await message.answer(
            "❌ *Unsubscribed successfully!*\n\n"
            "You will no longer receive water alerts.\n"
            "Use /subscribe to reactivate your subscription.",
            parse_mode="Markdown"
        )
        logger.info(f"User unsubscribed: {chat_id}")
    else:
        await message.answer(
            "ℹ️ You are not currently subscribed.\n\n"
            "Use /subscribe to start receiving water alerts.",
            parse_mode="Markdown"
        )


@router.message(Command("status"))
async def cmd_status(message: Message):
    chat_id = message.chat.id
    user = user_db.get_user(chat_id)

    if user:
        status_emoji = "✅" if user.is_active else "❌"
        status_text = "Active" if user.is_active else "Inactive"

        last_notified_text = "Never"
        if user.last_notified:
            last_notified_text = user.last_notified.strftime('%Y-%m-%d %H:%M')

        status_message = f"""
{status_emoji} *Subscription Status: {status_text}*

*User Info:*
• Chat ID: `{user.chat_id}`
• Username: @{user.username or 'N/A'}
• Name: {user.first_name or ''} {user.last_name or ''}

*Subscription Details:*
• Location: *{user.location}*
• Subscribed since: {user.subscribed_at.strftime('%Y-%m-%d %H:%M')}
• Last notification: {last_notified_text}
        """

        await message.answer(status_message, parse_mode="Markdown")
    else:
        await message.answer(
            "ℹ️ *No subscription found.*\n\n"
            "Use /subscribe to start receiving water alerts.",
            parse_mode="Markdown"
        )


@router.message(Command("check"))
async def cmd_check(message: Message):
    chat_id = message.chat.id

    await message.answer("🔍 Checking for water alerts...", parse_mode="Markdown")

    try:
        scraper = WaterScraper()
        alerts = scraper.get_data()

        if not alerts:
            await message.answer(
                "ℹ️ *No water alerts found.*\n\n"
                "There are currently no water supply alerts",
                parse_mode="Markdown"
            )
            return

        # Send each alert
        for alert in alerts:
            alert_message = f"""
*Water Alert*

*{alert['title']}*

{alert['message']}

🔗 [View the source]({alert['url']})
            """
            await message.answer(alert_message, parse_mode="Markdown")

        logger.info(f"Manual check performed by user {chat_id}, found {len(alerts)} alerts")

    except Exception as e:
        logger.error(f"Error checking alerts for user {chat_id}: {e}", exc_info=True)
        await message.answer(
            "❌ *Error checking alerts*\n\n"
            "Sorry, there was an error retrieving water alerts. Please try again later.",
            parse_mode="Markdown"
        )


@router.message(F.text)
async def handle_text(message: Message):
    await message.answer(
        "ℹ️ I don't understand that command\n\n"
        "Use /help to see available commands",
        parse_mode="Markdown"
    )
