from typing import Any

from app.scrapers.base_scraper import BaseScraper


class FacebookScraper(BaseScraper):
    source_name = "facebook"

    async def scrape(self, query: str, location: str, **kwargs: Any) -> list[dict[str, Any]]:
        return []
