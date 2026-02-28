def generate_email_patterns(first_name: str, last_name: str, domain: str) -> list[str]:
    first = (first_name or "").strip().lower()
    last = (last_name or "").strip().lower()
    if not first or not last or not domain:
        return []

    fi = first[0]
    li = last[0]
    return [
        f"{first}@{domain}",
        f"{first}.{last}@{domain}",
        f"{first}{last}@{domain}",
        f"{fi}{last}@{domain}",
        f"{fi}.{last}@{domain}",
        f"{first}_{last}@{domain}",
        f"{first}-{last}@{domain}",
        f"{last}.{first}@{domain}",
        f"{li}{first}@{domain}",
    ]
