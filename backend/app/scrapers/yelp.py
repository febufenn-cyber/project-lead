from typing import Any

from app.scrapers.base_scraper import BaseScraper


class YelpScraper(BaseScraper):
    source_name = "yelp"

    async def scrape(self, query: str, location: str, **kwargs: Any) -> list[dict[str, Any]]:
        return []
