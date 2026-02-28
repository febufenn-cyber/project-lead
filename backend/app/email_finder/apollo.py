"""Apollo.io API client for contact/email discovery."""

from typing import Any

import httpx

from app.config import get_settings


class ApolloClient:
    BASE_URL = "https://api.apollo.io/api/v1"

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = (settings.apollo_api_key or "").strip()
        self.timeout = settings.request_timeout_seconds

    def _has_key(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "x-api-key": self.api_key,
        }

    async def domain_search(
        self,
        domain: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for people at domain. Returns list with email, first_name, last_name, title."""
        if not self._has_key() or not (domain or "").strip():
            return []

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(
                    f"{self.BASE_URL}/mixed_people/search",
                    headers=self._headers(),
                    json={
                        "api_key": self.api_key,
                        "q_organization_domains": domain.strip(),
                        "page": 1,
                        "per_page": limit,
                    },
                )
                r.raise_for_status()
                data = r.json()
        except Exception:
            return []

        people = data.get("people") or []
        return [
            {
                "email": p.get("email"),
                "first_name": p.get("first_name"),
                "last_name": p.get("last_name"),
                "position": p.get("title"),
                "confidence": 80 if p.get("email") else 0,
                "linkedin_url": p.get("linkedin_url"),
            }
            for p in people
            if p.get("email")
        ]

    async def find_email(
        self,
        domain: str,
        first_name: str,
        last_name: str,
    ) -> dict[str, Any] | None:
        """Find email for person at domain using Apollo."""
        people = await self.domain_search(domain, limit=20)
        first = (first_name or "").strip().lower()
        last = (last_name or "").strip().lower()
        for p in people:
            fn = (p.get("first_name") or "").strip().lower()
            ln = (p.get("last_name") or "").strip().lower()
            if fn == first and ln == last:
                return {
                    "email": p.get("email"),
                    "first_name": p.get("first_name"),
                    "last_name": p.get("last_name"),
                    "position": p.get("position"),
                    "confidence": p.get("confidence", 70),
                }
        return people[0] if people else None
