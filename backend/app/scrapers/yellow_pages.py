from typing import Any
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup

from app.config import get_settings
from app.scrapers.base_scraper import BaseScraper


class YellowPagesScraper(BaseScraper):
    source_name = "yellow_pages"
    BASE_URL = "https://www.yellowpages.com"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_minute=10, **kwargs)
        settings = get_settings()
        self.timeout = settings.request_timeout_seconds

    async def scrape(
        self,
        query: str,
        location: str,
        max_results: int = 40,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        page = 1
        per_page = 30

        while len(normalized) < max_results:
            await self.rate_limiter.wait()
            url = (
                f"{self.BASE_URL}/search"
                f"?search_terms={quote_plus(query)}"
                f"&geo_location_terms={quote_plus(location)}"
                f"&page={page}"
            )
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        ),
                        "Accept": "text/html,application/xhtml+xml",
                        "Accept-Language": "en-US,en;q=0.9",
                    },
                ) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    html = response.text
            except httpx.HTTPError:
                break

            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select(".result, .search-result, .srp-listing, .v-card")
            if not cards:
                cards = soup.select("[class*='result']")
            if not cards:
                break

            for i, card in enumerate(cards):
                if len(normalized) >= max_results:
                    break

                name_elem = card.select_one(
                    ".business-name, .n a, a[class*='business-name'], .org, h2 a"
                )
                name = (name_elem.get_text(strip=True) if name_elem else None) or f"Business {i}"

                link_elem = card.select_one("a[href*='yellowpages.com/mip/']")
                yp_href = link_elem.get("href") if link_elem else None
                external_id = yp_href.split("/")[-1].split("?")[0] if yp_href else f"yp_{page}_{i}"

                phone_elem = card.select_one(".phones, .phone, [class*='phone']")
                phone = phone_elem.get_text(strip=True) if phone_elem else None

                addr_elem = card.select_one(".adr, .street-address, .address, [class*='address']")
                street = addr_elem.get_text(strip=True) if addr_elem else None

                locality = card.select_one(".locality")
                city = locality.get_text(strip=True) if locality else None

                region = card.select_one(".region")
                state = region.get_text(strip=True) if region else None

                website_elem = card.select_one("a.track-visit-website, a[href*='http']:not([href*='yellowpages'])")
                website = None
                if website_elem and website_elem.get("href"):
                    href = website_elem["href"]
                    if href.startswith("http"):
                        website = href
                    else:
                        website = urljoin(self.BASE_URL, href)

                normalized.append(
                    self.normalize(
                        {
                            "name": name,
                            "website": website,
                            "phone": phone,
                            "address": street,
                            "city": city,
                            "state": state,
                            "external_id": external_id,
                            "raw": {"card_html": str(card)[:500], "href": yp_href},
                        }
                    )
                )

            if len(cards) < per_page:
                break
            page += 1
            if page > 5:
                break

        return normalized
