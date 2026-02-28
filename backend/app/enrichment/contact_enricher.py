"""Contact enrichment - merges email finder results into lead data."""

from typing import Any

from app.email_finder.finder_engine import EmailFinderEngine
from app.email_finder.verifier import EmailVerifier


class ContactEnricher:
    """Enrich contact/lead with email finding and verification."""

    def __init__(self) -> None:
        self.finder = EmailFinderEngine()
        self.verifier = EmailVerifier()

    async def enrich(self, contact: dict[str, Any]) -> dict[str, Any]:
        """Find and verify email, merge into contact."""
        enriched = dict(contact)
        domain = enriched.get("company_domain") or _domain_from_url(enriched.get("company_website"))
        if not domain:
            return enriched

        first = enriched.get("contact_first_name") or enriched.get("first_name")
        last = enriched.get("contact_last_name") or enriched.get("last_name")

        candidates = await self.finder.find_emails(
            domain=domain,
            first_name=first,
            last_name=last,
            limit=3,
        )

        for c in candidates:
            verdict = await self.verifier.verify(c.email)
            if verdict.status == "valid":
                enriched["contact_email"] = c.email
                enriched["company_email"] = c.email
                enriched["email_found"] = True
                enriched["email_verified"] = True
                if c.first_name:
                    enriched["contact_first_name"] = c.first_name
                if c.last_name:
                    enriched["contact_last_name"] = c.last_name
                if c.position:
                    enriched["contact_title"] = c.position
                break

        if candidates and not enriched.get("contact_email"):
            enriched["contact_email"] = candidates[0].email
            enriched["email_found"] = True
            enriched["email_verified"] = False

        return enriched


def _domain_from_url(url: str | None) -> str | None:
    if not url:
        return None
    from urllib.parse import urlparse
    return urlparse(url).netloc.replace("www.", "") or None
