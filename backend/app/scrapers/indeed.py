from typing import Any

from app.scrapers.base_scraper import BaseScraper


class IndeedScraper(BaseScraper):
    source_name = "indeed"

    async def scrape(self, query: str, location: str, **kwargs: Any) -> list[dict[str, Any]]:
        return []
