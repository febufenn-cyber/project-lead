"""Broker-specific search query templates for finding real estate and car clients (buyers/sellers)."""

from typing import Optional

# Real estate: people wanting to buy or sell (not brokers/agencies)
REAL_ESTATE_QUERIES = [
    '"sell my house" {location}',
    '"want to sell my home" {location}',
    '"sell my property" {location}',
    '"first time home buyer" {location}',
    '"looking to buy house" {location}',
    '"buy a house" {location}',
    '"need to sell house fast" {location}',
]

# Cars: people wanting to buy or sell (not dealerships/brokers)
CAR_QUERIES = [
    '"sell my car" {location}',
    '"want to sell my car" {location}',
    '"sell my vehicle" {location}',
    '"buy used car" {location}',
    '"looking to buy a car" {location}',
]

# Generic fallback when industry is not real_estate or cars
GENERIC_QUERIES = [
    "{query} {location}",
]


def get_broker_queries(industry: Optional[str], query: str, location: str) -> list[str]:
    """
    Return search query strings for broker use case.
    Uses intent-based phrases for real estate and cars to find clients, not brokers.
    """
    loc = location or ""
    q = query or ""

    if industry and industry.strip().lower() in ("real_estate", "real estate", "realestate"):
        return [t.format(location=loc) for t in REAL_ESTATE_QUERIES]
    if industry and industry.strip().lower() in ("cars", "car", "auto", "automotive"):
        return [t.format(location=loc) for t in CAR_QUERIES]

    # Generic: use user query + location
    return [t.format(query=q, location=loc)]
