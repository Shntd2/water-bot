import requests
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup
import re
from typing import Optional, List, Dict, Any, Tuple
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from config.config import settings as scraper_settings
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


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
        self.request_timeout = request_timeout or scraper_settings.REQUEST_TIMEOUT
        self.max_items = max_items or scraper_settings.MAX_REPOSITORIES

        self.session = self._setup_session()

        self.cache = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers or scraper_settings.MAX_WORKERS)

    def _setup_session(self) -> requests.Session:
        session = requests.Session()

        adapter = HTTPAdapter(
            pool_connections=scraper_settings.POOL_CONNECTIONS,
            pool_maxsize=scraper_settings.POOL_MAXSIZE,
            max_retries=scraper_settings.MAX_RETRIES,
            pool_block=scraper_settings.POOL_BLOCK
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        })

        return session

    def is_cache_valid(self, cache_key: str) -> bool:
        if cache_key not in self.cache:
            return False

        cached_time = self.cache[cache_key].get('timestamp')
        if not cached_time:
            return False

        elapsed_seconds = (datetime.now() - cached_time).total_seconds()
        is_valid = elapsed_seconds < self.cache_timeout

        return is_valid

    def _make_request(self, url: str, params: Dict = None) -> requests.Response:
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.request_timeout,
                stream=True
            )
            response.raise_for_status()
            return response
        except requests.Timeout:
            logger.error(f"Request timeout for {url} (timeout: {self.request_timeout}s)")
            raise
        except requests.ConnectionError as e:
            logger.error(f"Connection error for {url}: {e}")
            raise
        except requests.HTTPError as e:
            logger.error(f"HTTP error for {url}: {e} (status: {e.response.status_code})")
            raise
        except requests.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            raise

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
            if hasattr(self, 'session'):
                self.session.close()
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
