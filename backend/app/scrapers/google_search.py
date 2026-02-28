"""Google Custom Search scraper - finds client intent (buyers/sellers) for brokers."""

import logging
from typing import Any
from urllib.parse import urlparse

from app.config import get_settings
from app.providers.broker_queries import get_broker_queries
from app.providers.google_custom_search import GoogleCustomSearchClient
from app.scrapers.base_scraper import BaseScraper
from app.utils.contact_parser import extract_contact_info

logger = logging.getLogger(__name__)


def _clean_title(title: str) -> str:
    """Remove trailing site name, pipe, dash artifacts."""
    if not title:
        return "Unknown"
    for sep in (" - ", " | ", " – ", " — "):
        if sep in title:
            title = title.split(sep)[0].strip()
    return title.strip() or "Unknown"


def _infer_intent(industry: str | None, query_phrase: str) -> dict[str, str]:
    """Infer lead intent from industry and query used."""
    intent = {"industry": industry or "general", "intent": "unknown"}
    q = (query_phrase or "").lower()
    if "sell" in q and ("house" in q or "home" in q or "property" in q):
        intent["intent"] = "seller"
        intent["category"] = "real_estate"
    elif "buy" in q and ("house" in q or "home" in q):
        intent["intent"] = "buyer"
        intent["category"] = "real_estate"
    elif "sell" in q and ("car" in q or "vehicle" in q):
        intent["intent"] = "seller"
        intent["category"] = "car"
    elif "buy" in q and ("car" in q or "vehicle" in q):
        intent["intent"] = "buyer"
        intent["category"] = "car"
    return intent


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
        industry: str | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        if not self.client.api_key or not self.client.engine_id:
            return []

        # Broker-specific: multiple intent queries for real estate & cars
        search_phrases = get_broker_queries(industry, query, location)
        per_query = max(5, max_results // len(search_phrases))
        seen_urls: set[str] = set()
        all_normalized: list[dict[str, Any]] = []

        for phrase in search_phrases:
            if len(all_normalized) >= max_results:
                break
            await self.rate_limiter.wait()
            items = await self.client.search(
                query=phrase,
                location=None,  # phrase already includes location
                max_results=per_query,
            )
            intent_info = _infer_intent(industry, phrase)

            for i, item in enumerate(items):
                link = (item.get("link") or "").strip()
                if link in seen_urls:
                    continue
                seen_urls.add(link)

                title = item.get("title") or ""
                snippet = item.get("snippet") or ""
                display_link = item.get("displayLink") or ""
                combined_text = f"{title} {snippet}"

                # Step 3: Parse contact info from snippet
                contact = extract_contact_info(combined_text)
                email = contact.get("email")
                phone = contact.get("phone")

                domain = urlparse(link).netloc.replace("www.", "") if link else display_link
                company_name = _clean_title(title)

                raw = {
                    "name": company_name,
                    "company_name": company_name,
                    "website": link,
                    "company_website": link,
                    "external_id": link or f"search_{hash(phrase) % 10**8}_{i}",
                    "company_phone": phone,
                    "company_email": email,
                    "contact_email": email,
                    "raw": {"item": item, "snippet": snippet, "intent": intent_info},
                    "intent": intent_info,
                    "source_urls": [link] if link else [],
                    "email_found": bool(email),
                }

                normalized = self.normalize(raw)
                normalized["source_urls"] = [link] if link else []
                normalized["raw_data"] = raw.get("raw", raw)
                normalized["company_email"] = email
                normalized["contact_email"] = email
                normalized["email_found"] = bool(email)
                all_normalized.append(normalized)

                if len(all_normalized) >= max_results:
                    break

        return all_normalized
