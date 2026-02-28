from typing import Any

from app.scrapers.base_scraper import BaseScraper


class BingSearchScraper(BaseScraper):
    source_name = "bing_search"

    async def scrape(self, query: str, location: str, **kwargs: Any) -> list[dict[str, Any]]:
        return []
