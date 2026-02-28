from typing import Any

from app.scrapers.base_scraper import BaseScraper


class IndustryDirectoriesScraper(BaseScraper):
    source_name = "industry_directories"

    async def scrape(self, query: str, location: str, **kwargs: Any) -> list[dict[str, Any]]:
        return []
