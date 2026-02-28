from typing import Any
from urllib.parse import urlparse

from app.config import get_settings
from app.providers.google_custom_search import GoogleCustomSearchClient
from app.scrapers.base_scraper import BaseScraper


class GoogleSearchScraper(BaseScraper):
    source_name = "google_search"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_minute=20, **kwargs)
        settings = get_settings()
        self.client = GoogleCustomSearchClient(
            api_key=settings.google_custom_search_api_key or "",
            engine_id=settings.google_custom_search_engine_id or "",
            timeout_seconds=settings.request_timeout_seconds,
        )

    async def scrape(
        self,
        query: str,
        location: str,
        max_results: int = 40,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        if not self.client.api_key or not self.client.engine_id:
            return []

        await self.rate_limiter.wait()
        items = await self.client.search(
            query=query,
            location=location,
            max_results=max_results,
        )

        normalized: list[dict[str, Any]] = []
        for i, item in enumerate(items):
            title = item.get("title") or "Unknown"
            link = item.get("link") or ""
            snippet = item.get("snippet") or ""
            display_link = item.get("displayLink") or ""
            domain = urlparse(link).netloc.replace("www.", "") if link else display_link

            normalized.append(
                self.normalize(
                    {
                        "name": title,
                        "website": link,
                        "external_id": link or f"search_{i}",
                        "raw": {"item": item, "snippet": snippet},
                    }
                )
            )
        return normalized
