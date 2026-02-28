"""Normalized lead DTO used between scrapers and Lead ORM model."""

from typing import Any
from urllib.parse import urlparse
from uuid import UUID


def _domain_from_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    host = parsed.netloc.lower().replace("www.", "")
    return host or None


class NormalizedLead:
    """Canonical shape for raw scraper output before persistence as Lead."""

    def __init__(
        self,
        *,
        source: str,
        external_id: str | None = None,
        company_name: str,
        company_domain: str | None = None,
        company_website: str | None = None,
        company_phone: str | None = None,
        company_email: str | None = None,
        street: str | None = None,
        city: str | None = None,
        state: str | None = None,
        country: str | None = None,
        zip_code: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        rating: float | None = None,
        review_count: int | None = None,
        raw_data: dict[str, Any] | None = None,
        data_sources: list[str] | None = None,
    ):
        self.source = source
        self.external_id = external_id
        self.company_name = company_name or "Unknown"
        self.company_domain = company_domain or _domain_from_url(company_website)
        self.company_website = company_website
        self.company_phone = company_phone
        self.company_email = company_email
        self.street = street
        self.city = city
        self.state = state
        self.country = country
        self.zip_code = zip_code
        self.latitude = latitude
        self.longitude = longitude
        self.rating = rating
        self.review_count = review_count
        self.raw_data = raw_data or {}
        self.data_sources = data_sources or [source]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "external_id": self.external_id,
            "company_name": self.company_name,
            "company_domain": self.company_domain,
            "company_website": self.company_website,
            "company_phone": self.company_phone,
            "company_email": self.company_email,
            "street": self.street,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "zip_code": self.zip_code,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "rating": self.rating,
            "review_count": self.review_count,
            "raw_data": self.raw_data,
            "data_sources": self.data_sources,
        }


def normalize_to_lead_payload(
    raw: dict[str, Any],
    source: str,
    job_id: UUID,
    lead_score: int = 0,
) -> dict[str, Any]:
    """Map raw scraper dict to Lead ORM payload."""
    company_website = raw.get("company_website") or raw.get("website")
    company_name = raw.get("company_name") or raw.get("name") or "Unknown"
    external_id = raw.get("external_id")
    company_email = raw.get("company_email") or raw.get("email")
    contact_email = raw.get("contact_email") or company_email

    payload = {
        "job_id": job_id,
        "source": source,
        "external_id": external_id,
        "company_name": company_name,
        "company_domain": _domain_from_url(company_website),
        "company_website": company_website,
        "company_phone": raw.get("company_phone") or raw.get("phone"),
        "company_email": company_email,
        "street": raw.get("street") or raw.get("address"),
        "city": raw.get("city"),
        "state": raw.get("state"),
        "country": raw.get("country"),
        "zip_code": raw.get("zip_code"),
        "latitude": raw.get("latitude"),
        "longitude": raw.get("longitude"),
        "rating": raw.get("rating"),
        "review_count": raw.get("review_count"),
        "lead_score": lead_score,
        "raw_data": raw.get("raw_data", raw),
        "data_sources": raw.get("data_sources", [source]),
    }

    # Optional fields (Lead model allows None)
    if contact_email:
        payload["contact_email"] = contact_email
    if raw.get("source_urls"):
        payload["source_urls"] = raw["source_urls"]
    if raw.get("email_found") is not None:
        payload["email_found"] = bool(raw["email_found"])

    return payload
