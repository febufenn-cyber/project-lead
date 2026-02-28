from typing import Any

from app.scrapers.base_scraper import BaseScraper


class LinkedInScraper(BaseScraper):
    source_name = "linkedin"

    async def scrape(self, query: str, location: str, **kwargs: Any) -> list[dict[str, Any]]:
        return []
