import math


def score_lead(*, rating: float | None, review_count: int | None, website: str | None, phone: str | None, address: str | None) -> int:
    score = 0

    if rating is not None:
        normalized = max(0.0, min(5.0, rating))
        score += int((normalized / 5.0) * 40)

    if review_count:
        score += min(25, int(math.log10(review_count + 1) * 12))

    if website:
        score += 15

    if phone:
        score += 10

    if address:
        score += 5

    if review_count and review_count >= 100:
        score += 5

    return min(100, score)
