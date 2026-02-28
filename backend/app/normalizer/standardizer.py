from typing import Any
from urllib.parse import urlparse


def _domain_from_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    host = parsed.netloc.lower().replace("www.", "")
    return host or None


class LeadStandardizer:
    """Maps raw records from scrapers to canonical Lead fields."""

    FIELD_MAP = {
        "name": "company_name",
        "website": "company_website",
        "phone": "company_phone",
        "email": "company_email",
        "address": "street",
        "formatted_address": "street",
    }

    def standardize(self, row: dict[str, Any]) -> dict[str, Any]:
        """Convert raw scraper output to canonical field names."""
        standardized = dict(row)
        for src, target in self.FIELD_MAP.items():
            if src in standardized and standardized.get(src) is not None:
                if target not in standardized or standardized.get(target) is None:
                    standardized[target] = standardized[src]
        if "company_website" in standardized and "company_domain" not in standardized:
            domain = _domain_from_url(standardized.get("company_website"))
            if domain:
                standardized["company_domain"] = domain
        return standardized
