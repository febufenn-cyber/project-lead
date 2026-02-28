from typing import Any, List, Optional

from app.email_finder.apollo import ApolloClient
from app.email_finder.hunter import HunterClient
from app.email_finder.pattern_guesser import generate_email_patterns
from app.email_finder.snov import SnovClient
from app.email_finder.verifier import EmailVerifier, VerificationResult


class EmailCandidate:
    def __init__(
        self,
        email: str,
        confidence: int = 0,
        source: str = "pattern",
        first_name: str | None = None,
        last_name: str | None = None,
        position: str | None = None,
    ):
        self.email = email
        self.confidence = confidence
        self.source = source
        self.first_name = first_name
        self.last_name = last_name
        self.position = position


class EmailFinderEngine:
    def __init__(self):
        self.hunter = HunterClient()
        self.snov = SnovClient()
        self.apollo = ApolloClient()
        self.verifier = EmailVerifier()

    async def find_emails(
        self,
        domain: str,
        person_name: Optional[str] = None,
        company_name: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        limit: int = 5,
    ) -> List[EmailCandidate]:
        """Find email candidates for domain, optionally for a specific person."""
        domain = (domain or "").strip().lower()
        if not domain:
            return []

        candidates: List[EmailCandidate] = []
        seen: set[str] = set()

        if first_name or last_name or person_name:
            first, last = first_name, last_name
            if person_name and not (first or last):
                parts = person_name.strip().split(None, 1)
                first = parts[0] if parts else ""
                last = parts[1] if len(parts) > 1 else ""
            if first or last:
                hunter_result = await self.hunter.email_finder(domain, first or "?", last or "?")
                if hunter_result and hunter_result.get("email"):
                    email = hunter_result["email"].lower()
                    if email not in seen:
                        seen.add(email)
                        candidates.append(
                            EmailCandidate(
                                email=email,
                                confidence=hunter_result.get("confidence", 80),
                                source="hunter",
                                first_name=hunter_result.get("first_name"),
                                last_name=hunter_result.get("last_name"),
                                position=hunter_result.get("position"),
                            )
                        )

                apollo_result = await self.apollo.find_email(domain, first or "", last or "")
                if apollo_result and apollo_result.get("email"):
                    email = apollo_result["email"].lower()
                    if email not in seen:
                        seen.add(email)
                        candidates.append(
                            EmailCandidate(
                                email=email,
                                confidence=apollo_result.get("confidence", 70),
                                source="apollo",
                                first_name=apollo_result.get("first_name"),
                                last_name=apollo_result.get("last_name"),
                                position=apollo_result.get("position"),
                            )
                        )

        hunter_emails = await self.hunter.domain_search(domain, limit=limit)
        for e in hunter_emails:
            email = (e.get("email") or "").lower()
            if email and email not in seen:
                seen.add(email)
                candidates.append(
                    EmailCandidate(
                        email=email,
                        confidence=e.get("confidence", 50),
                        source="hunter",
                        first_name=e.get("first_name"),
                        last_name=e.get("last_name"),
                        position=e.get("position"),
                    )
                )

        apollo_emails = await self.apollo.domain_search(domain, limit=limit)
        for e in apollo_emails:
            email = (e.get("email") or "").lower()
            if email and email not in seen:
                seen.add(email)
                candidates.append(
                    EmailCandidate(
                        email=email,
                        confidence=e.get("confidence", 60),
                        source="apollo",
                        first_name=e.get("first_name"),
                        last_name=e.get("last_name"),
                        position=e.get("position"),
                    )
                )

        snov_emails = await self.snov.domain_search(domain, limit=limit)
        for e in snov_emails:
            email = (e.get("email") or "").lower()
            if email and email not in seen:
                seen.add(email)
                candidates.append(
                    EmailCandidate(
                        email=email,
                        confidence=e.get("confidence", 50),
                        source="snov",
                        first_name=e.get("first_name"),
                        last_name=e.get("last_name"),
                        position=e.get("position"),
                    )
                )

        if not candidates and (first_name or last_name):
            first = (first_name or "").strip().lower()
            last = (last_name or "").strip().lower()
            for pattern in generate_email_patterns(first, last, domain)[:5]:
                if pattern.lower() not in seen:
                    seen.add(pattern.lower())
                    candidates.append(
                        EmailCandidate(email=pattern, confidence=30, source="pattern")
                    )

        candidates.sort(key=lambda c: c.confidence, reverse=True)
        return candidates[:limit]

    async def find_email(self, first_name: str, last_name: str, domain: str) -> dict[str, Any]:
        """Legacy single-email finder. Returns best candidate with verification."""
        candidates = await self.find_emails(
            domain=domain,
            first_name=first_name,
            last_name=last_name,
            limit=5,
        )
        best = None
        for c in candidates:
            verdict = await self.verifier.verify(c.email)
            if verdict.status == "valid" and (best is None or verdict.confidence > best.get("confidence", 0)):
                best = {
                    "email": c.email,
                    "status": verdict.status,
                    "reason": verdict.reason,
                    "confidence": verdict.confidence,
                }
        return best or {"email": None, "status": "unknown", "confidence": 0}
