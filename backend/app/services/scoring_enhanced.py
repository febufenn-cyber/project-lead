"""Enhanced lead scoring that layers an AI-derived bonus on top of the base score."""

from typing import Any

from app.scoring import score_lead


def _ai_adoption_bonus(readiness: str) -> int:
    return {"low": 0, "medium": 10, "high": 25}.get(str(readiness).lower(), 0)


def _urgency_bonus(urgency_score: int | float) -> int:
    """Scale 1-10 urgency into 0-20 bonus points."""
    try:
        val = max(1, min(10, int(urgency_score)))
    except (TypeError, ValueError):
        return 0
    return int((val - 1) / 9 * 20)


def _size_bonus(estimated_size: str) -> int:
    return {
        "micro": 0,
        "small": 5,
        "medium": 15,
        "large": 25,
        "enterprise": 25,
    }.get(str(estimated_size).lower(), 0)


def _pain_point_bonus(pain_points: list) -> int:
    """Up to 15 pts based on number of identified pain points (max 5 useful)."""
    count = len(pain_points) if isinstance(pain_points, list) else 0
    return min(15, count * 3)


def score_enriched_lead(
    *,
    rating: float | None,
    review_count: int | None,
    website: str | None,
    phone: str | None,
    address: str | None,
    ai_enrichment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a scoring breakdown dict.

    Keys: total_score, base_score, ai_bonus, grade, priority
    """
    base_score = score_lead(
        rating=rating,
        review_count=review_count,
        website=website,
        phone=phone,
        address=address,
    )

    ai_bonus = 0
    if ai_enrichment:
        ai_bonus += _ai_adoption_bonus(ai_enrichment.get("ai_adoption_readiness", "low"))
        ai_bonus += _urgency_bonus(ai_enrichment.get("urgency_score", 1))
        ai_bonus += _size_bonus(ai_enrichment.get("estimated_size", "micro"))
        ai_bonus += _pain_point_bonus(ai_enrichment.get("pain_points", []))

    total_score = min(100, base_score + ai_bonus)

    if total_score >= 80:
        grade = "A"
        priority = "hot"
    elif total_score >= 60:
        grade = "B"
        priority = "warm"
    elif total_score >= 40:
        grade = "C"
        priority = "cold"
    else:
        grade = "D"
        priority = "cold"

    return {
        "total_score": total_score,
        "base_score": base_score,
        "ai_bonus": ai_bonus,
        "grade": grade,
        "priority": priority,
    }
