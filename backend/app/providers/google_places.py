import asyncio
from typing import Any

import httpx


class GooglePlacesClient:
    TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

    def __init__(self, api_key: str, timeout_seconds: int = 20):
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    async def search(self, *, query: str, location: str, max_results: int) -> list[dict[str, Any]]:
        if not self.api_key:
            return []

        collected: list[dict[str, Any]] = []
        next_page_token: str | None = None

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            while len(collected) < max_results:
                params: dict[str, Any] = {
                    "query": f"{query} in {location}",
                    "key": self.api_key,
                }

                if next_page_token:
                    # Google Places requires a short delay before next-page tokens become valid.
                    await asyncio.sleep(2.1)
                    params["pagetoken"] = next_page_token

                response = await client.get(self.TEXT_SEARCH_URL, params=params)
                response.raise_for_status()
                payload = response.json()

                status = payload.get("status")
                if status in {"ZERO_RESULTS", None}:
                    break
                if status not in {"OK", "ZERO_RESULTS"}:
                    raise RuntimeError(f"Google Places error: {status}")

                page_items = payload.get("results", [])
                for place in page_items:
                    collected.append(place)
                    if len(collected) >= max_results:
                        break

                next_page_token = payload.get("next_page_token")
                if not next_page_token:
                    break

        return collected

    async def details(self, place_id: str) -> dict[str, Any]:
        if not self.api_key:
            return {}

        fields = ",".join(
            [
                "name",
                "formatted_address",
                "formatted_phone_number",
                "website",
                "address_components",
                "url",
                "international_phone_number",
            ]
        )

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(
                self.PLACE_DETAILS_URL,
                params={"place_id": place_id, "fields": fields, "key": self.api_key},
            )
            response.raise_for_status()
            payload = response.json()

        if payload.get("status") != "OK":
            return {}

        return payload.get("result", {})
