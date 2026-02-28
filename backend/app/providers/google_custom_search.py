"""Google Custom Search JSON API client."""

from typing import Any

import httpx


class GoogleCustomSearchClient:
    API_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, api_key: str, engine_id: str, timeout_seconds: int = 20):
        self.api_key = api_key
        self.engine_id = engine_id
        self.timeout_seconds = timeout_seconds

    async def search(
        self,
        *,
        query: str,
        location: str | None = None,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Search and return list of result items (title, link, snippet)."""
        if not self.api_key or not self.engine_id:
            return []

        search_query = f"{query} {location}" if location else query
        collected: list[dict[str, Any]] = []
        start = 1

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            while len(collected) < max_results:
                params = {
                    "key": self.api_key,
                    "cx": self.engine_id,
                    "q": search_query,
                    "start": start,
                    "num": min(10, max_results - len(collected)),
                }
                response = await client.get(self.API_URL, params=params)
                response.raise_for_status()
                payload = response.json()

                for item in payload.get("items", []):
                    collected.append(item)
                    if len(collected) >= max_results:
                        break

                next_page = payload.get("queries", {}).get("nextPage") or []
                next_start = next_page[0].get("startIndex") if next_page else None
                if next_start is None or next_start > 90:  # API limit 100 results
                    break
                start = next_start

        return collected
