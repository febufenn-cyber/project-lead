"""Company enrichment via external APIs."""

from typing import Any

import httpx

from app.config import get_settings


class CompanyEnricher:
    """Enrich company data using Clearbit, Crunchbase, BuiltWith when keys are available."""

    def __init__(self) -> None:
        settings = get_settings()
        self.clearbit_key = (getattr(settings, "clearbit_api_key", None) or "").strip()
        self.timeout = getattr(settings, "request_timeout_seconds", 20)

    async def enrich(self, company: dict[str, Any]) -> dict[str, Any]:
        """Merge enrichment data into company dict."""
        enriched = dict(company)
        domain = enriched.get("company_domain") or _domain_from_website(enriched.get("company_website"))

        if not domain:
            return enriched

        if self.clearbit_key:
            clearbit_data = await self._clearbit_enrich(domain)
            if clearbit_data:
                enriched.setdefault("raw_data", {})["clearbit"] = clearbit_data
                if clearbit_data.get("company"):
                    c = clearbit_data["company"]
                    enriched["industry"] = c.get("industry") or enriched.get("industry")
                    enriched["employee_count"] = c.get("metrics", {}).get("employees") or enriched.get("employee_count")
                    enriched["description"] = c.get("description") or enriched.get("description")

        return enriched

    async def _clearbit_enrich(self, domain: str) -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.get(
                    f"https://company.clearbit.com/v2/companies/find?domain={domain}",
                    auth=(self.clearbit_key, ""),
                )
                if r.status_code == 200:
                    return r.json()
        except Exception:
            pass
        return None


def _domain_from_website(url: str | None) -> str | None:
    if not url:
        return None
    from urllib.parse import urlparse
    return urlparse(url).netloc.replace("www.", "") or None
