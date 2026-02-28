from typing import Any

from app.scrapers.base_scraper import BaseScraper


class GovernmentRegistryScraper(BaseScraper):
    source_name = "government_registry"

    async def scrape(self, query: str, location: str, **kwargs: Any) -> list[dict[str, Any]]:
        return []
