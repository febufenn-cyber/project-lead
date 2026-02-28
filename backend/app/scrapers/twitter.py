from typing import Any

from app.scrapers.base_scraper import BaseScraper


class TwitterScraper(BaseScraper):
    source_name = "twitter"

    async def scrape(self, query: str, location: str, **kwargs: Any) -> list[dict[str, Any]]:
        return []
