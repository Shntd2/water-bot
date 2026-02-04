import asyncio
from aiogram.handlers import MessageHandler
from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any, Union
from app.services.telegram_service import telegram_service
import logging
logger = logging.getLogger(__name__)


router = APIRouter(tags=["bot_control"])

bot_state: Dict[str, Union[bool, dict, Optional[MessageHandler], Optional[asyncio.Task], Any]] = {
    "is_running": False,
    "bot_info": {},
    "message_handler": None,
    "polling_task": None
}


@router.post("/start-bot")
async def start_bot():
    global bot_state

    try:
        if bot_state["is_running"]:
            return {"status": "already_running", "message": "Bot is already running"}

        if not bot_state["message_handler"]:
            bot_state["message_handler"] = MessageHandler()

        bot_info = await telegram_service.get_me()
        if not bot_info.get("ok"):
            raise HTTPException(status_code=400, detail="Failed to connect to Telegram. Check TELEGRAM_BOT_TOKEN")

        bot_state["bot_info"] = bot_info.get("result", {})

        message_handler = bot_state["message_handler"]
        bot_state["polling_task"] = asyncio.create_task(
            telegram_service.start_polling(message_handler)
        )
        bot_state["is_running"] = True

        return {
            "status": "started",
            "bot_info": bot_state["bot_info"],
            "message": "Bot polling started successfully"
        }

    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop-bot")
async def stop_bot():
    global bot_state

    try:
        if not bot_state["is_running"]:
            return {"status": "not_running", "message": "Bot is not running"}

        telegram_service.stop_polling()

        polling_task = bot_state["polling_task"]
        if polling_task and not polling_task.cancelled():
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                pass

        bot_state["polling_task"] = None
        bot_state["is_running"] = False

        return {"status": "stopped", "message": "Bot polling stopped successfully"}

    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))