from typing import Any

from app.scrapers.base_scraper import BaseScraper


class CrunchbaseScraper(BaseScraper):
    source_name = "crunchbase"

    async def scrape(self, query: str, location: str, **kwargs: Any) -> list[dict[str, Any]]:
        return []
