"""Intent detection - aggregate signals into intent score."""

from typing import Any


def compute_intent_score(signals: list[dict[str, Any]]) -> int:
    """Aggregate intent signals into 0-100 score."""
    if not signals:
        return 0
    total = sum(float(s.get("score", 0)) for s in signals)
    count = len(signals)
    avg = total / count if count else 0
    boosted = avg * (1 + min(count - 1, 5) * 0.1)  # More signals = higher confidence
    return min(100, int(boosted))


class IntentDetector:
    """Detect intent from lead data and signals."""

    def detect(self, lead: dict[str, Any], signals: list[dict[str, Any]] | None = None) -> int:
        """Compute intent score from lead attributes and optional signals."""
        score = 0
        if lead.get("review_count", 0) and lead.get("review_count", 0) > 50:
            score += 20
        if lead.get("rating", 0) and lead.get("rating", 0) >= 4.2:
            score += 20
        if lead.get("company_website") or lead.get("website"):
            score += 15
        if lead.get("email_found") or lead.get("contact_email"):
            score += 15
        if signals:
            score = max(score, compute_intent_score(signals))
        return min(100, score)
