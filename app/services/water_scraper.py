import re
from typing import Optional, List, Dict, Any, Tuple
import logging
from datetime import datetime
from app.config.settings import settings

from app.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class WaterScraper(BaseScraper):
    BASE_URL = settings.BASE_URL

    def __init__(self,
                 cache_timeout: int = None,
                 max_workers: int = None,
                 request_timeout: int = None,
                 max_items: int = None):

        super().__init__(
            base_url=self.BASE_URL,
            cache_timeout=cache_timeout,
            max_workers=max_workers,
            request_timeout=request_timeout,
            max_items=max_items
        )

    def get_cache_key(self, location: Optional[str] = None) -> str:
        return "water_alerts_all"

    async def get_data(self, location: Optional[str] = None) -> List[Dict[str, Any]]:
        cache_key = self.get_cache_key()

        if self.is_cache_valid(cache_key):
            return self.cache[cache_key]['data']

        try:
            alerts = []

            for page_num in range(1, 6):
                logger.info(f"Scraping page {page_num} for water alerts")

                url = f"{self.base_url}?page={page_num}" if page_num > 1 else self.base_url

                try:
                    response = await self._make_request(url)
                    soup = self._parse_html(response.content)

                    accordion_links = soup.find_all('a', class_=['accordion-toggle', 'accordion-icon', 'link-unstyled', 'collapsed'])

                    logger.info(f"Found {len(accordion_links)} accordion links on page {page_num}")

                    for link in accordion_links:
                        alert_data = self._extract_item_data(link)
                        if alert_data:
                            alerts.append(alert_data)

                except Exception as e:
                    logger.warning(f"Failed to scrape page {page_num}: {e}")
                    continue

            self.cache[cache_key] = {
                'data': alerts,
                'timestamp': datetime.now()
            }
            logger.info(f"Scraped and cached {len(alerts)} total water alerts")
            return alerts

        except Exception as e:
            logger.error(f"Water scraping failed: {e}", exc_info=True)
            return self._handle_scraping_failure(cache_key)

    def _extract_item_data(self, element) -> Optional[Dict[str, Any]]:
        try:
            alert_data = {}

            raw_title = element.get_text().strip()
            alert_data['title'] = self.WHITESPACE_PATTERN.sub(' ', raw_title)

            panel = element.find_parent('div', class_='panel')
            if not panel:
                return None

            body_wrapper = panel.find('div', class_=re.compile(r'panel-collapse'))
            if not body_wrapper:
                return None

            panel_body = body_wrapper.find('div', class_='panel-body')
            if not panel_body:
                panel_body = body_wrapper.find('div', class_='panel body')

            message_parts = []
            if panel_body:
                for element in panel_body.descendants:
                    if element.name is None:
                        text = str(element).strip()
                        if text:
                            message_parts.append(text)

            alert_data['message'] = self.WHITESPACE_PATTERN.sub(' ', ' '.join(message_parts)).strip()

            alert_data['url'] = self.BASE_URL
            alert_data['published_at'] = datetime.now().isoformat()
            alert_data['story_id'] = str(hash(alert_data['title'] + alert_data['message']))

            return alert_data

        except Exception as e:
            logger.error(f"Error extracting water alert data: {e}", exc_info=True)
            return None

    @staticmethod
    def get_fallback_data() -> List[Dict[str, Any]]:
        return [
            {
                "title": "Water Alerts Unavailable",
                "message": "Could not retrieve water supply data",
                "published_at": datetime.now().isoformat(),
                "story_id": None
            }
        ]

    def get_warm_cache_queries(self) -> List[Tuple]:
        return []
