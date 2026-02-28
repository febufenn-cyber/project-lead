from typing import Any

from app.scrapers.base_scraper import BaseScraper


class ZoomInfoScraper(BaseScraper):
    source_name = "zoominfo"

    async def scrape(self, query: str, location: str, **kwargs: Any) -> list[dict[str, Any]]:
        return []
