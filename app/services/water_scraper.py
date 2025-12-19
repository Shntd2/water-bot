import re
from typing import Optional, List, Dict, Any, Tuple
import logging
from datetime import datetime
from app.config.settings import settings

from app.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class WaterScraper(BaseScraper):
    BASE_URL = settings.BASE_URL
    TARGET_LOCATION = settings.TARGET_LOCATION

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
        return f"water_alerts_{location or 'default'}"

    def get_data(self, location: Optional[str] = None) -> List[Dict[str, Any]]:
        search_term = location if location else self.TARGET_LOCATION
        cache_key = self.get_cache_key(search_term)

        if self.is_cache_valid(cache_key):
            return self.cache[cache_key]['data']

        try:
            url = self.base_url
            response = self._make_request(url)
            soup = self._parse_html(response.content)

            alerts = []
            panel_group = soup.find('div', class_=re.compile(r'panel-group.*accordion'))

            if panel_group:
                panels = panel_group.find_all('div', class_='panel')

                for panel in panels:
                    alert_data = self._extract_item_data(panel)
                    if alert_data and search_term in alert_data['title']:
                        alerts.append(alert_data)

            self.cache[cache_key] = {
                'data': alerts,
                'timestamp': datetime.now()
            }
            return alerts

        except Exception as e:
            logger.error(f"Water scraping failed for {cache_key}: {e}", exc_info=True)
            return self._handle_scraping_failure(cache_key)

    def _extract_item_data(self, panel) -> Optional[Dict[str, Any]]:
        try:
            alert_data = {}

            # Try to find accordion link in panel-heading first, then directly in panel
            heading = panel.find('div', class_='panel-heading')
            search_container = heading if heading else panel

            title_link = search_container.find('a', class_=re.compile(r'accordion-toggle'))
            if not title_link:
                return None

            raw_title = title_link.get_text().strip()
            alert_data['title'] = self.WHITESPACE_PATTERN.sub(' ', raw_title)

            body_wrapper = panel.find('div', class_=re.compile(r'panel-collapse'))
            if not body_wrapper:
                return None

            panel_body = body_wrapper.find('div',
                                           class_='panel-body')
            if not panel_body:
                panel_body = body_wrapper.find('div', class_='panel body')

            message_parts = []
            if panel_body:
                child_divs = panel_body.find_all('div')
                for div in child_divs:
                    text = div.get_text(strip=True)
                    if text:
                        message_parts.append(text)

            alert_data['message'] = "\n".join(message_parts)

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
        return [
            (self.TARGET_LOCATION,),
        ]
