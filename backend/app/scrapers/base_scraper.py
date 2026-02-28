from abc import ABC, abstractmethod
from typing import Any

from app.utils.rate_limiter import RateLimiter


class BaseScraper(ABC):
    """Abstract base for all scrapers. Returns normalized dicts compatible with Lead model."""

    source_name = "base"
    default_max_results = 40

    def __init__(
        self,
        rate_limiter: RateLimiter | None = None,
        requests_per_minute: int = 30,
    ):
        self.rate_limiter = rate_limiter or RateLimiter(requests_per_minute=requests_per_minute)

    @abstractmethod
    async def scrape(
        self,
        query: str,
        location: str,
        max_results: int = 40,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        Scrape and return list of normalized lead dicts.
        Each dict should have: company_name, company_website, company_phone,
        street/city/state/country/zip_code, external_id, source, raw_data.
        """
        raise NotImplementedError

    def normalize(self, data: dict[str, Any]) -> dict[str, Any]:
        """Convert raw record to normalized shape."""
        raw = data.get("raw") or data
        return {
            "company_name": data.get("company_name") or data.get("name") or "Unknown",
            "company_website": data.get("company_website") or data.get("website"),
            "company_phone": data.get("company_phone") or data.get("phone"),
            "company_email": data.get("company_email") or data.get("email"),
            "city": data.get("city"),
            "state": data.get("state"),
            "country": data.get("country"),
            "street": data.get("street") or data.get("address"),
            "zip_code": data.get("zip_code"),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "rating": data.get("rating"),
            "review_count": data.get("review_count"),
            "external_id": data.get("external_id"),
            "source": self.source_name,
            "raw_data": raw,
            "data_sources": [self.source_name],
        }
