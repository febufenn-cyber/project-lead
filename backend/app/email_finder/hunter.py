"""Hunter.io API client for email discovery."""

from typing import Any

import httpx

from app.config import get_settings


class HunterClient:
    BASE_URL = "https://api.hunter.io/v2"

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = (settings.hunter_api_key or "").strip()
        self.timeout = settings.request_timeout_seconds

    def _has_key(self) -> bool:
        return bool(self.api_key)

    async def domain_search(
        self,
        domain: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Return emails found for domain. Each item: email, first_name, last_name, position, confidence."""
        if not self._has_key() or not (domain or "").strip():
            return []

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.get(
                    f"{self.BASE_URL}/domain-search",
                    params={
                        "domain": domain.strip(),
                        "api_key": self.api_key,
                        "limit": limit,
                    },
                )
                r.raise_for_status()
                data = r.json()
        except Exception:
            return []

        result = data.get("data", {})
        emails = result.get("emails") or []
        return [
            {
                "email": e.get("value"),
                "first_name": e.get("first_name"),
                "last_name": e.get("last_name"),
                "position": e.get("position"),
                "confidence": e.get("confidence", 0),
                "type": e.get("type", "personal"),
                "sources": e.get("sources", []),
            }
            for e in emails
            if e.get("value")
        ]

    async def email_finder(
        self,
        domain: str,
        first_name: str,
        last_name: str,
    ) -> dict[str, Any] | None:
        """Find most likely email for person at domain."""
        if not self._has_key() or not (domain or "").strip():
            return None

        first = (first_name or "").strip()
        last = (last_name or "").strip()
        if not first or not last:
            return None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.get(
                    f"{self.BASE_URL}/email-finder",
                    params={
                        "domain": domain.strip(),
                        "first_name": first,
                        "last_name": last,
                        "api_key": self.api_key,
                    },
                )
                r.raise_for_status()
                data = r.json()
        except Exception:
            return None

        result = data.get("data", {})
        email = result.get("email")
        if not email:
            return None
        return {
            "email": email,
            "first_name": result.get("first_name"),
            "last_name": result.get("last_name"),
            "position": result.get("position"),
            "confidence": result.get("score", 0),
            "sources": result.get("sources", []),
        }
