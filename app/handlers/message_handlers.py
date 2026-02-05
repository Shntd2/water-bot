import logging
from app.config.settings import settings
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

from app.services.user_service import user_service
from app.services.water_scraper import WaterScraper

logger = logging.getLogger(__name__)

router = Router()

AVAILABLE_LOCATIONS = settings.AVAILABLE_LOCATIONS


def create_location_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for location in AVAILABLE_LOCATIONS:
        buttons.append([InlineKeyboardButton(
            text=location,
            callback_data=f"location:{location}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(CommandStart())
async def cmd_start(message: Message):
    chat_id = message.chat.id
    user = user_service.get_user(chat_id)

    welcome_text = """
🛠️ *Welcome to Water Alert Bot!*

This bot monitors water supply alerts for Yerevan and sends you notifications.

*Available Commands:*
/subscribe - Subscribe to water alerts
/unsubscribe - Unsubscribe from alerts
/location - Change your location (once per day)
/status - Check your subscription status
/check - Check current water alerts
/help - Show this help message

You'll receive notifications when new water supply information is available.
    """

    await message.answer(welcome_text, parse_mode="Markdown")

    if not user or not user.location:
        await message.answer(
            "Please use /subscribe to choose your location and start receiving alerts.",
            parse_mode="Markdown"
        )


@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = """
🛠️ *Water Alert Bot Help*

*Available Commands:*
/start - Start the bot and subscribe
/subscribe - Subscribe to water alerts
/unsubscribe - Unsubscribe from alerts
/location - Change your location (you can change your location only once per day)
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
    user = user_service.get_user(chat_id)

    if user:
        if user.is_active and user.location:
            await message.answer(
                "✅ You are already subscribed to water alerts!\n\n"
                f"Location: *{user.location}*\n"
                f"Subscribed since: {user.subscribed_at.strftime('%Y-%m-%d %H:%M')}",
                parse_mode="Markdown"
            )
        elif not user.location:
            await message.answer(
                "📍 *Please select your location:*\n\n"
                "Choose your district in Yerevan to receive water alerts:",
                reply_markup=create_location_keyboard(),
                parse_mode="Markdown"
            )
        else:
            user_service.update_user(chat_id, is_active=True)
            await message.answer(
                "✅ *Subscription reactivated!*\n\n"
                f"You will now receive water alerts again for: *{user.location}*",
                parse_mode="Markdown"
            )
            logger.info(f"User resubscribed: {chat_id}")
    else:
        user_service.add_user(
            chat_id=chat_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            location=None,
            is_active=True
        )
        logger.info(f"New user created: {chat_id} (@{message.from_user.username})")

        await message.answer(
            "📍 *Please select your location:*\n\n"
            "Choose your district in Yerevan to receive water alerts:",
            reply_markup=create_location_keyboard(),
            parse_mode="Markdown"
        )


@router.message(Command("location"))
async def cmd_change_location(message: Message):
    chat_id = message.chat.id
    user = user_service.get_user(chat_id)

    if not user or not user.is_active:
        await message.answer(
            "ℹ️ *Not subscribed*\n\n"
            "You need to be subscribed to change your location.\n"
            "Use /subscribe to get started.",
            parse_mode="Markdown"
        )
        return

    if not user.location:
        await message.answer(
            "ℹ️ *No location set*\n\n"
            "You haven't set a location yet. Use /subscribe to set your initial location.",
            parse_mode="Markdown"
        )
        return

    if user.last_location_changed:
        time_since_last_change = datetime.now() - user.last_location_changed
        hours_since_change = time_since_last_change.total_seconds() / 3600

        if hours_since_change < 24:
            hours_remaining = 24 - hours_since_change
            await message.answer(
                f"⏳ *Rate limit exceeded*\n\n"
                f"You can only change your location once per day.\n\n"
                f"Time remaining: *{int(hours_remaining)} hours {int((hours_remaining % 1) * 60)} minutes*\n\n"
                f"Please try again later.",
                parse_mode="Markdown"
            )
            logger.info(f"User {chat_id} attempted location change but hit rate limit")
            return

    await message.answer(
        f"📍 *Change your location*\n\n"
        f"Current location: *{user.location}*\n\n"
        f"Select a new location from the list below:",
        reply_markup=create_location_keyboard(),
        parse_mode="Markdown"
    )
    logger.info(f"User {chat_id} initiated location change")


@router.callback_query(F.data.startswith("location:"))
async def handle_location_selection(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    selected_location = callback.data.split(":", 1)[1]

    if selected_location not in AVAILABLE_LOCATIONS:
        await callback.answer("Invalid location selected", show_alert=True)
        return

    user = user_service.get_user(chat_id)
    if not user:
        await callback.answer("User not found. Please try /subscribe again.", show_alert=True)
        return

    is_location_change = user.location is not None
    old_location = user.location

    update_data = {"location": selected_location}

    if is_location_change:
        update_data["last_location_changed"] = datetime.now()

    user_service.update_user(chat_id, **update_data)

    if is_location_change:
        logger.info(f"User {chat_id} changed location from {old_location} to {selected_location}")
        await callback.message.edit_text(
            f"✅ *Location changed successfully!*\n\n"
            f"Previous location: *{old_location}*\n"
            f"New location: *{selected_location}*\n\n"
            f"You will now receive water alerts for your new location.",
            parse_mode="Markdown"
        )
        await callback.answer("Location changed successfully!")
    else:
        logger.info(f"User {chat_id} selected location: {selected_location}")
        await callback.message.edit_text(
            f"✅ *Successfully subscribed!*\n\n"
            f"You will receive water alerts for: *{selected_location}*",
            parse_mode="Markdown"
        )
        await callback.answer("Location saved successfully!")


@router.message(Command("unsubscribe"))
async def cmd_unsubscribe(message: Message):
    chat_id = message.chat.id
    user = user_service.get_user(chat_id)

    if user and user.is_active:
        user_service.update_user(chat_id, is_active=False)
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
    user = user_service.get_user(chat_id)

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
    user = user_service.get_user(chat_id)

    if not user or not user.location:
        await message.answer(
            "ℹ️ *No location set*\n\n"
            "Please use /subscribe to set your location first.",
            parse_mode="Markdown"
        )
        return

    await message.answer("🔍 Checking for water alerts...", parse_mode="Markdown")

    try:
        scraper = WaterScraper()
        alerts = await scraper.get_data(location=user.location)

        if not alerts:
            await message.answer(
                f"ℹ️ *No water alerts found for {user.location}*\n\n"
                "There are currently no water supply alerts for your location.",
                parse_mode="Markdown"
            )
            return

        for alert in alerts:
            alert_message = f"""
*Water Alert*

*{alert['title']}*

{alert['message']}

🔗 [View the source]({alert['url']})
            """
            await message.answer(alert_message, parse_mode="Markdown")

        logger.info(f"Manual check performed by user {chat_id}, found {len(alerts)} alerts for {user.location}")

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
