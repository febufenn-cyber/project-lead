from typing import Any

from app.scrapers.base_scraper import BaseScraper


class InstagramScraper(BaseScraper):
    source_name = "instagram"

    async def scrape(self, query: str, location: str, **kwargs: Any) -> list[dict[str, Any]]:
        return []
