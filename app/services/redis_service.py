import logging
from typing import Optional
import redis.asyncio as redis
from app.config.settings import settings

logger = logging.getLogger(__name__)


class RedisService:

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.ttl = settings.REDIS_ALERT_TTL

    async def connect(self):
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                ssl_cert_reqs=None,
                socket_connect_timeout=5,
                socket_keepalive=True,
            )
            await self.redis_client.ping()
            logger.info(f"Connected to Redis using URL: {settings.REDIS_URL.split('@')[-1] if '@' in settings.REDIS_URL else settings.REDIS_URL.split('//')[1].split(':')[0]}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}", exc_info=True)
            raise

    async def close(self):
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")

    def _get_user_key(self, chat_id: int) -> str:
        return f"sent_alerts:{chat_id}"

    async def has_alert_been_sent(self, chat_id: int, alert_id: str) -> bool:
        if not self.redis_client:
            logger.warning("Redis client not connected, returning False")
            return False

        try:
            key = self._get_user_key(chat_id)
            result = await self.redis_client.sismember(key, alert_id)
            return bool(result)
        except Exception as e:
            logger.error(f"Error checking sent alert for user {chat_id}: {e}", exc_info=True)
            return False

    async def mark_alert_as_sent(self, chat_id: int, alert_id: str) -> bool:
        if not self.redis_client:
            logger.warning("Redis client not connected, cannot mark alert")
            return False

        try:
            key = self._get_user_key(chat_id)

            await self.redis_client.sadd(key, alert_id)

            await self.redis_client.expire(key, self.ttl)

            logger.debug(f"Marked alert {alert_id} as sent to user {chat_id} with TTL {self.ttl}s")
            return True
        except Exception as e:
            logger.error(f"Error marking alert as sent for user {chat_id}: {e}", exc_info=True)
            return False

    async def get_sent_alerts_count(self, chat_id: int) -> int:
        if not self.redis_client:
            return 0

        try:
            key = self._get_user_key(chat_id)
            count = await self.redis_client.scard(key)
            return count
        except Exception as e:
            logger.error(f"Error getting sent alerts count for user {chat_id}: {e}", exc_info=True)
            return 0

    async def clear_user_alerts(self, chat_id: int) -> bool:
        if not self.redis_client:
            return False

        try:
            key = self._get_user_key(chat_id)
            await self.redis_client.delete(key)
            logger.info(f"Cleared sent alerts for user {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Error clearing alerts for user {chat_id}: {e}", exc_info=True)
            return False


redis_service = RedisService()
