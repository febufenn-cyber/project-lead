"""Snov.io API client for email discovery."""

from typing import Any

import httpx

from app.config import get_settings


class SnovClient:
    BASE_URL = "https://app.snov.io/restapi"

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = (settings.snov_api_key or "").strip()
        self.timeout = settings.request_timeout_seconds

    def _has_key(self) -> bool:
        return bool(self.api_key)

    async def domain_search(
        self,
        domain: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get emails for domain via Snov domain search."""
        if not self._has_key() or not (domain or "").strip():
            return []

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(
                    f"{self.BASE_URL}/get-domain-emails-with-info",
                    params={"access_token": self.api_key},
                    json={"domain": domain.strip()},
                )
                r.raise_for_status()
                data = r.json()
        except Exception:
            return []

        emails = data if isinstance(data, list) else data.get("emails") or data.get("data") or []
        result: list[dict[str, Any]] = []
        for e in emails[:limit]:
            if isinstance(e, dict):
                email = e.get("email") or e.get("address")
                if email:
                    result.append({
                        "email": email,
                        "first_name": e.get("first_name"),
                        "last_name": e.get("last_name"),
                        "position": e.get("job"),
                        "confidence": e.get("confidence", 50),
                    })
        return result
