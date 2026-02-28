from typing import Any

from app.config import get_settings
from app.providers.google_places import GooglePlacesClient
from app.scrapers.base_scraper import BaseScraper


class GoogleMapsScraper(BaseScraper):
    source_name = "google_maps"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_minute=30, **kwargs)
        settings = get_settings()
        self.client = GooglePlacesClient(
            api_key=settings.google_places_api_key,
            timeout_seconds=settings.request_timeout_seconds,
        )

    async def scrape(
        self,
        query: str,
        location: str,
        max_results: int = 40,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        max_results = max_results or int(kwargs.get("max_results", 40))
        rows = await self.client.search(query=query, location=location, max_results=max_results)
        normalized: list[dict[str, Any]] = []

        for place in rows:
            details = {}
            place_id = place.get("place_id")
            if place_id:
                details = await self.client.details(place_id)

            comp = details.get("address_components") or []

            def pick(kind: str) -> str | None:
                for c in comp:
                    if kind in c.get("types", []):
                        return c.get("long_name")
                return None

            normalized.append(
                self.normalize(
                    {
                        "name": place.get("name"),
                        "website": details.get("website"),
                        "phone": details.get("formatted_phone_number") or details.get("international_phone_number"),
                        "address": details.get("formatted_address") or place.get("formatted_address"),
                        "city": pick("locality"),
                        "state": pick("administrative_area_level_1"),
                        "country": pick("country"),
                        "zip_code": pick("postal_code"),
                        "latitude": place.get("geometry", {}).get("location", {}).get("lat"),
                        "longitude": place.get("geometry", {}).get("location", {}).get("lng"),
                        "rating": place.get("rating"),
                        "review_count": place.get("user_ratings_total"),
                        "external_id": place.get("place_id"),
                        "raw": {"place": place, "details": details},
                    }
                )
            )

        return normalized
