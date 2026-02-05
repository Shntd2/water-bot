from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from bs4 import BeautifulSoup
import re
from typing import Optional, List, Dict, Any, Tuple
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from config.config import settings as scraper_settings
from abc import ABC, abstractmethod
import random

logger = logging.getLogger(__name__)


class PlaywrightResponse:
    def __init__(self, content: bytes, status_code: int, url: str):
        self.content = content
        self.status_code = status_code
        self.url = url

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"{self.status_code} Error for url: {self.url}")


class BaseScraper(ABC):
    WHITESPACE_PATTERN = re.compile(r'\s+')
    NUMBER_PATTERN = re.compile(r'\d+')

    def __init__(self,
                 base_url: str,
                 cache_timeout: int = None,
                 max_workers: int = None,
                 request_timeout: int = None,
                 max_items: int = None):

        self.base_url = base_url
        self.cache_timeout = cache_timeout or scraper_settings.CACHE_TIMEOUT
        self.request_timeout = (request_timeout or scraper_settings.REQUEST_TIMEOUT) * 1000
        self.max_items = max_items or scraper_settings.MAX_REPOSITORIES

        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._setup_browser()

        self.cache = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers or scraper_settings.MAX_WORKERS)

    def _setup_browser(self):
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu',
                ]
            )

            self._context = self._browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='America/New_York',
                java_script_enabled=True,
            )

            self._context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                window.chrome = {runtime: {}};
            """)

            self._page = self._context.new_page()
            self._warm_up_session()
            logger.info("Playwright browser initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Playwright browser: {e}")
            raise

    def _warm_up_session(self):
        try:
            logger.info(f"Warming up session with base URL: {self.base_url}")
            self._page.goto(self.base_url, wait_until='networkidle', timeout=self.request_timeout)
            self._page.wait_for_timeout(random.randint(2000, 4000))
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

    def _make_request(self, url: str, params: Dict = None, max_retries: int = 3) -> PlaywrightResponse:
        if params:
            query_string = '&'.join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{query_string}" if '?' not in url else f"{url}&{query_string}"

        last_exception = None

        for attempt in range(max_retries):
            try:
                delay = random.uniform(1.0, 3.0) if attempt == 0 else random.uniform(3.0, 6.0) * (attempt + 1)
                self._page.wait_for_timeout(int(delay * 1000))

                response = self._page.goto(url, wait_until='networkidle', timeout=self.request_timeout)

                if response is None:
                    raise Exception(f"No response received for {url}")

                status_code = response.status

                if status_code == 403:
                    logger.warning(f"403 Forbidden for {url}, attempt {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        backoff = (2 ** attempt) * random.uniform(2.0, 4.0)
                        logger.info(f"Retrying in {backoff:.1f}s...")
                        self._page.wait_for_timeout(int(backoff * 1000))
                        continue
                    raise Exception(f"403 Client Error: Forbidden for url: {url}")

                if status_code >= 400:
                    raise Exception(f"{status_code} Error for url: {url}")

                content = self._page.content().encode('utf-8')
                return PlaywrightResponse(content=content, status_code=status_code, url=url)

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

    def __del__(self):
        try:
            if hasattr(self, 'executor'):
                self.executor.shutdown(wait=False)
            if hasattr(self, '_page') and self._page:
                self._page.close()
            if hasattr(self, '_context') and self._context:
                self._context.close()
            if hasattr(self, '_browser') and self._browser:
                self._browser.close()
            if hasattr(self, '_playwright') and self._playwright:
                self._playwright.stop()
        except Exception:
            pass

    @abstractmethod
    def get_cache_key(self, *args, **kwargs) -> str:
        pass

    @abstractmethod
    def get_data(self, *args, **kwargs) -> List[Dict[str, Any]]:
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
