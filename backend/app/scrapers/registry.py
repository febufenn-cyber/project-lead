"""Registry of available scrapers by source name."""

from typing import Any

from app.scrapers.base_scraper import BaseScraper
from app.scrapers.google_maps import GoogleMapsScraper
from app.scrapers.google_search import GoogleSearchScraper
from app.scrapers.yellow_pages import YellowPagesScraper

# Source aliases for backward compatibility
SOURCE_ALIASES = {
    "google_places": "google_maps",
}

REGISTRY: dict[str, type[BaseScraper]] = {
    "google_maps": GoogleMapsScraper,
    "google_places": GoogleMapsScraper,
    "google_search": GoogleSearchScraper,
    "yellow_pages": YellowPagesScraper,
}

DEFAULT_SOURCES = ["google_maps"]


def resolve_source(source: str) -> str:
    """Resolve alias to canonical source name."""
    return SOURCE_ALIASES.get(source, source)


def get_scraper(source: str) -> BaseScraper | None:
    """Get scraper instance for source, or None if not supported."""
    canonical = resolve_source(source.strip().lower())
    klass = REGISTRY.get(canonical)
    if not klass:
        return None
    return klass()


def get_available_sources() -> list[str]:
    """Return list of unique canonical source names."""
    seen: set[str] = set()
    out: list[str] = []
    for s in REGISTRY:
        canonical = resolve_source(s)
        if canonical not in seen:
            seen.add(canonical)
            out.append(canonical)
    return sorted(out)
