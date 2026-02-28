"""Email verification: MX check, disposable/free-provider tagging."""

import re
from dataclasses import dataclass
from typing import Optional, Set

DISPOSABLE_DOMAINS: Set[str] = {
    "tempmail.com", "guerrillamail.com", "mailinator.com", "throwaway.email",
    "10minutemail.com", "temp-mail.org", "fakeinbox.com", "trashmail.com",
    "yopmail.com", "maildrop.cc", "getnada.com", "dispostable.com",
}

FREE_PROVIDERS: Set[str] = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "live.com",
    "icloud.com", "aol.com", "mail.com", "protonmail.com", "zoho.com",
}


@dataclass
class VerificationResult:
    status: str  # valid, invalid, risky, catch_all, unknown
    reason: Optional[str] = None
    confidence: int = 0
    is_disposable: bool = False
    is_free_provider: bool = False
    mx_valid: bool = False


class EmailVerifier:
    """Verify email deliverability via MX records and heuristics."""

    EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    async def verify(self, email: str) -> VerificationResult:
        if not email or "@" not in email:
            return VerificationResult(status="invalid", reason="malformed", confidence=0)

        email = email.strip().lower()
        if not self.EMAIL_REGEX.match(email):
            return VerificationResult(status="invalid", reason="malformed", confidence=0)

        local, domain = email.split("@", 1)
        domain_lower = domain.lower()

        is_disposable = domain_lower in DISPOSABLE_DOMAINS
        is_free = domain_lower in FREE_PROVIDERS

        if is_disposable:
            return VerificationResult(
                status="invalid",
                reason="disposable",
                confidence=0,
                is_disposable=True,
            )

        mx_valid = await self._check_mx(domain)
        if not mx_valid:
            return VerificationResult(
                status="invalid",
                reason="no_mx_records",
                confidence=10,
            )

        if is_free:
            return VerificationResult(
                status="valid",
                reason="free_provider",
                confidence=60,
                is_free_provider=True,
                mx_valid=True,
            )

        return VerificationResult(
            status="valid",
            reason="mx_ok",
            confidence=80,
            mx_valid=True,
        )

    async def _check_mx(self, domain: str) -> bool:
        """Check if domain has MX records."""
        try:
            import dns.resolver
            answers = dns.resolver.resolve(domain, "MX")
            return len(answers) > 0
        except Exception:
            try:
                import socket
                socket.getaddrinfo(domain, None)
                return True
            except Exception:
                return False
