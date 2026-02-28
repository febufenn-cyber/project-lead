"""Lead scoring - rule-based and ML-ready feature extraction."""

import math
from typing import Any

from app.scoring import score_lead


def extract_features(lead: dict[str, Any]) -> dict[str, float]:
    """Extract numeric features for ML scoring."""
    rating = lead.get("rating")
    review_count = lead.get("review_count") or 0
    website = lead.get("company_website") or lead.get("website")
    phone = lead.get("company_phone") or lead.get("phone")
    address = lead.get("street") or lead.get("address")

    return {
        "rating_norm": max(0.0, min(5.0, float(rating or 0)) / 5.0),
        "review_log": math.log10(review_count + 1) if review_count else 0,
        "has_website": 1.0 if website else 0.0,
        "has_phone": 1.0 if phone else 0.0,
        "has_address": 1.0 if address else 0.0,
        "high_review_count": 1.0 if review_count and review_count >= 50 else 0.0,
    }


class LeadScorer:
    """Score leads using rules (extensible to ML model)."""

    def score(self, lead: dict[str, Any]) -> int:
        return score_lead(
            rating=lead.get("rating"),
            review_count=lead.get("review_count"),
            website=lead.get("company_website") or lead.get("website"),
            phone=lead.get("company_phone") or lead.get("phone"),
            address=lead.get("street") or lead.get("address"),
        )
