"""Extract contact info (email, phone) from text snippets."""

import re

# Common false-positive domains to exclude
SKIP_EMAIL_DOMAINS = {
    "example.com", "domain.com", "email.com", "yoursite.com",
    "sentry.io", "wixpress.com", "google.com", "facebook.com",
    "twitter.com", "linkedin.com", "youtube.com", "instagram.com",
}


def extract_emails(text: str) -> list[str]:
    """Extract valid-looking business emails from text. Skips generic/example domains."""
    if not text or not isinstance(text, str):
        return []
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    found = re.findall(pattern, text)
    out = []
    for e in found:
        domain = e.split("@")[-1].lower()
        if domain in SKIP_EMAIL_DOMAINS:
            continue
        # Skip obvious placeholders
        if any(x in e.lower() for x in ["@example", "noreply", "no-reply", "email@"]):
            continue
        out.append(e)
    return list(dict.fromkeys(out))  # preserve order, dedupe


def extract_phones(text: str) -> list[str]:
    """Extract phone numbers from text (US-style and international)."""
    if not text or not isinstance(text, str):
        return []
    # US: (xxx) xxx-xxxx, xxx-xxx-xxxx, xxx.xxx.xxxx, 10+ digits
    us_pattern = r"(?:\+1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}"
    # International: +country code...
    intl_pattern = r"\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}"
    matches = re.findall(us_pattern, text) + re.findall(intl_pattern, text)
    # Clean and dedupe
    cleaned = []
    for m in matches:
        digits = re.sub(r"\D", "", m)
        if len(digits) >= 10 and digits not in [re.sub(r"\D", "", x) for x in cleaned]:
            cleaned.append(m)
    return cleaned


def extract_contact_info(text: str) -> dict:
    """Extract email and phone from text. Returns first of each if multiple."""
    emails = extract_emails(text or "")
    phones = extract_phones(text or "")
    return {
        "email": emails[0] if emails else None,
        "phone": phones[0] if phones else None,
    }
