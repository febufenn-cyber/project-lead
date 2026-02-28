from urllib.parse import urlparse


def build_dedupe_key(lead: dict, source: str | None = None) -> str:
    """
    Build deduplication key for multi-source leads.
    Uses place:<id>, yellow_pages:<id>, google_search:<id>, etc.
    """
    external_id = lead.get("external_id")
    src = source or lead.get("source", "unknown")
    if external_id:
        return f"{src}:{external_id}"

    name = (lead.get("company_name") or lead.get("name") or "").strip().lower()
    website = lead.get("company_website") or lead.get("website") or ""
    host = urlparse(website).netloc.replace("www.", "").lower() if website else ""
    street = (lead.get("street") or lead.get("address") or "").strip().lower()
    return f"fallback:{name}|{host}|{street}"


class LeadDeduplicator:
    def key(self, lead: dict, source: str | None = None) -> str:
        return build_dedupe_key(lead, source)

    def dedupe(self, leads: list[dict], source: str | None = None) -> list[dict]:
        seen: set[str] = set()
        out: list[dict] = []
        for lead in leads:
            k = self.key(lead, source)
            if k in seen:
                continue
            seen.add(k)
            out.append(lead)
        return out
