import logging
from typing import Optional
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.config.settings import settings

logger = logging.getLogger(__name__)


class TelegramService:

    def __init__(self):
        self._bot: Optional[Bot] = None
        self._dispatcher: Optional[Dispatcher] = None

    async def get_session(self) -> tuple[Bot, Dispatcher]:
        if self._bot is not None and self._dispatcher is not None:
            logger.info("Reusing existing Telegram session")
            return self._bot, self._dispatcher

        try:
            self._bot = Bot(
                token=settings.TELEGRAM_BOT_TOKEN,
                default=DefaultBotProperties(
                    parse_mode=ParseMode.MARKDOWN
                )
            )

            self._dispatcher = Dispatcher()

            logger.info("Telegram session initialized successfully")
            return self._bot, self._dispatcher

        except Exception as e:
            logger.error(f"Failed to initialize Telegram session: {e}", exc_info=True)
            await self.close_session()
            raise

    async def close_session(self):
        try:
            if self._bot:
                if self._bot.session:
                    await self._bot.session.close()
                self._bot = None
                logger.info("Bot session closed")

            self._dispatcher = None

            logger.info("Telegram session closed successfully")

        except Exception as e:
            logger.error(f"Error closing Telegram session: {e}", exc_info=True)

    async def setup_webhook(self, webhook_url: str, secret_token: Optional[str] = None) -> bool:
        if not self._bot:
            logger.error("Bot not initialized. Call get_session() first.")
            return False

        try:
            await self._bot.delete_webhook(drop_pending_updates=True)
            logger.info("Deleted existing webhook")

            webhook_info = await self._bot.set_webhook(
                url=webhook_url,
                secret_token=secret_token if secret_token else None,
                allowed_updates=["message", "callback_query", "inline_query"],
                drop_pending_updates=False
            )

            if webhook_info:
                logger.info(f"Webhook set successfully: {webhook_url}")

                webhook_info = await self._bot.get_webhook_info()
                logger.info(f"Webhook info: {webhook_info}")
                return True
            else:
                logger.error("Failed to set webhook")
                return False

        except Exception as e:
            logger.error(f"Error setting webhook: {e}", exc_info=True)
            return False

    async def delete_webhook(self) -> bool:
        if not self._bot:
            logger.error("Bot not initialized. Call get_session() first.")
            return False

        try:
            await self._bot.delete_webhook(drop_pending_updates=True)
            logger.info("Webhook deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Error deleting webhook: {e}", exc_info=True)
            return False

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: Optional[str] = None,
        disable_web_page_preview: bool = True,
    ) -> bool:
        if not self._bot:
            logger.error("Bot not initialized. Call get_session() first.")
            return False

        try:
            await self._bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode or settings.TELEGRAM_PARSE_MODE,
                disable_web_page_preview=disable_web_page_preview,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {chat_id}: {e}", exc_info=True)
            return False

    async def send_chat_action(self, chat_id: int, action: Optional[str] = None) -> bool:
        if not self._bot:
            logger.error("Bot not initialized. Call get_session() first.")
            return False

        try:
            await self._bot.send_chat_action(
                chat_id=chat_id,
                action=action or settings.TELEGRAM_DEFAULT_CHAT_ACTION,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send chat action to {chat_id}: {e}", exc_info=True)
            return False

    @property
    def bot(self) -> Optional[Bot]:
        return self._bot

    @property
    def dispatcher(self) -> Optional[Dispatcher]:
        return self._dispatcher


telegram_service = TelegramService()
