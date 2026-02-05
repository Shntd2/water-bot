from curl_cffi import AsyncSession
from bs4 import BeautifulSoup
import re
from typing import Optional, List, Dict, Any, Tuple
import logging
from datetime import datetime
from abc import ABC, abstractmethod
import asyncio
import random

from config.config import settings as scraper_settings

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    WHITESPACE_PATTERN = re.compile(r'\s+')
    NUMBER_PATTERN = re.compile(r'\d+')

    BROWSER_IMPERSONATIONS = [
        "chrome136",
        "chrome133a",
        "chrome131",
        "chrome124",
        "chrome123",
    ]

    def __init__(self,
                 base_url: str,
                 cache_timeout: int = None,
                 max_workers: int = None,
                 request_timeout: int = None,
                 max_items: int = None):

        self.base_url = base_url
        self.cache_timeout = cache_timeout or scraper_settings.CACHE_TIMEOUT
        self.request_timeout = request_timeout or scraper_settings.REQUEST_TIMEOUT
        self.max_items = max_items or scraper_settings.MAX_REPOSITORIES

        self._session: Optional[AsyncSession] = None
        self._impersonate = random.choice(self.BROWSER_IMPERSONATIONS)

        self.cache = {}

    async def _get_session(self) -> AsyncSession:
        if self._session is None:
            self._session = AsyncSession(
                impersonate=self._impersonate,
                timeout=self.request_timeout,
                headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0',
                },
            )
            await self._warm_up_session()
        return self._session

    async def _warm_up_session(self):
        try:
            logger.info(f"Warming up session with base URL: {self.base_url} (impersonate: {self._impersonate})")
            await self._session.get(self.base_url)
            await asyncio.sleep(random.uniform(1.0, 2.0))
            logger.info("Session warm-up completed")
        except Exception as e:
            logger.warning(f"Session warm-up failed: {e}")

    def is_cache_valid(self, cache_key: str) -> bool:
        if cache_key not in self.cache:
            return False

        cached_time = self.cache[cache_key].get('timestamp')
        if not cached_time:
            return False

        elapsed_seconds = (datetime.now() - cached_time).total_seconds()
        is_valid = elapsed_seconds < self.cache_timeout

        return is_valid

    async def _make_request(self, url: str, params: Dict = None, max_retries: int = 3):
        session = await self._get_session()
        last_exception = None

        for attempt in range(max_retries):
            try:
                delay = random.uniform(1.0, 3.0) if attempt == 0 else random.uniform(3.0, 6.0) * (attempt + 1)
                await asyncio.sleep(delay)

                response = await session.get(url, params=params)

                if response.status_code == 403:
                    logger.warning(f"403 Forbidden for {url}, attempt {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        self._impersonate = random.choice(self.BROWSER_IMPERSONATIONS)
                        self._session = None
                        session = await self._get_session()
                        backoff = (2 ** attempt) * random.uniform(2.0, 4.0)
                        logger.info(f"Retrying with {self._impersonate} in {backoff:.1f}s...")
                        await asyncio.sleep(backoff)
                        continue
                    raise Exception(f"403 Client Error: Forbidden for url: {url}")

                response.raise_for_status()
                return response

            except Exception as e:
                last_exception = e
                if "403" not in str(e):
                    logger.error(f"Request failed for {url}: {e}")
                    raise

        if last_exception:
            logger.error(f"All retries exhausted for {url}: {last_exception}")
            raise last_exception

    def _parse_html(self, content: bytes) -> BeautifulSoup:
        try:
            return BeautifulSoup(content, 'lxml')
        except Exception:
            return BeautifulSoup(content, 'html.parser')

    def _handle_scraping_failure(self, cache_key: str) -> List[Dict[str, Any]]:
        if cache_key in self.cache:
            logger.warning(f"Returning cached data for {cache_key} due to scraping failure")
            return self.cache[cache_key]['data']

        logger.warning(f"No cache available for {cache_key}, returning fallback data")
        return self.get_fallback_data()

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None

    @abstractmethod
    def get_cache_key(self, *args, **kwargs) -> str:
        pass

    @abstractmethod
    async def get_data(self, *args, **kwargs) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def _extract_item_data(self, element) -> Optional[Dict[str, Any]]:
        pass

    @staticmethod
    @abstractmethod
    def get_fallback_data() -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_warm_cache_queries(self) -> List[Tuple]:
        pass
