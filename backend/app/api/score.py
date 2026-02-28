"""Lead scoring and intent API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.intelligence.intent_detector import IntentDetector
from app.intelligence.lead_scorer import LeadScorer
from app.models import IntentSignal, Lead

router = APIRouter(prefix="/score", tags=["score"])


class ScoreLeadResponse(BaseModel):
    lead_id: UUID
    lead_score: int
    intent_score: int


class BulkScoreRequest(BaseModel):
    lead_ids: list[UUID] = Field(max_length=100)


class BulkScoreResponse(BaseModel):
    results: list[ScoreLeadResponse]


@router.get("/lead/{lead_id}", response_model=ScoreLeadResponse)
async def score_lead(
    lead_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> ScoreLeadResponse:
    lead = await session.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead_dict = {
        "rating": lead.rating,
        "review_count": lead.review_count,
        "company_website": lead.company_website,
        "company_phone": lead.company_phone,
        "street": lead.street,
        "email_found": lead.email_found,
        "contact_email": lead.contact_email,
    }

    scorer = LeadScorer()
    lead_score = scorer.score(lead_dict)

    signals_result = await session.execute(
        select(IntentSignal).where(IntentSignal.lead_id == lead_id)
    )
    signals = [
        {"score": s.score, "signal_type": s.signal_type}
        for s in signals_result.scalars().all()
    ]
    intent_detector = IntentDetector()
    intent_score = intent_detector.detect(lead_dict, signals or None)

    return ScoreLeadResponse(
        lead_id=lead_id,
        lead_score=lead_score,
        intent_score=intent_score,
    )


@router.post("/bulk", response_model=BulkScoreResponse)
async def bulk_score(
    payload: BulkScoreRequest,
    session: AsyncSession = Depends(get_db),
) -> BulkScoreResponse:
    results = []
    for lead_id in payload.lead_ids:
        lead = await session.get(Lead, lead_id)
        if not lead:
            continue
        lead_dict = {
            "rating": lead.rating,
            "review_count": lead.review_count,
            "company_website": lead.company_website,
            "company_phone": lead.company_phone,
            "street": lead.street,
            "email_found": lead.email_found,
            "contact_email": lead.contact_email,
        }
        scorer = LeadScorer()
        lead_score = scorer.score(lead_dict)
        signals_result = await session.execute(
            select(IntentSignal).where(IntentSignal.lead_id == lead_id)
        )
        signals = [{"score": s.score} for s in signals_result.scalars().all()]
        intent_detector = IntentDetector()
        intent_score = intent_detector.detect(lead_dict, signals or None)
        results.append(
            ScoreLeadResponse(lead_id=lead_id, lead_score=lead_score, intent_score=intent_score)
        )
    return BulkScoreResponse(results=results)


@router.get("/intent/{lead_id}")
async def get_intent(
    lead_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> dict:
    lead = await session.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    signals_result = await session.execute(
        select(IntentSignal).where(IntentSignal.lead_id == lead_id).order_by(IntentSignal.detected_at.desc())
    )
    signals_list = signals_result.scalars().all()

    lead_dict = {
        "rating": lead.rating,
        "review_count": lead.review_count,
        "company_website": lead.company_website,
        "email_found": lead.email_found,
        "contact_email": lead.contact_email,
    }
    intent_detector = IntentDetector()
    signals = [{"score": s.score, "signal_type": s.signal_type} for s in signals_list]
    intent_score = intent_detector.detect(lead_dict, signals or None)

    return {
        "lead_id": str(lead_id),
        "intent_score": intent_score,
        "signals": [
            {"type": s.signal_type, "score": s.score, "detected_at": s.detected_at.isoformat() if s.detected_at else None}
            for s in signals_list
        ],
    }


class IntentSignalCreate(BaseModel):
    lead_id: UUID
    signal_type: str = Field(min_length=1, max_length=64)
    score: float = Field(default=0.5, ge=0, le=1)
    source: str | None = None


@router.post("/intent/signals")
async def add_intent_signal(
    payload: IntentSignalCreate,
    session: AsyncSession = Depends(get_db),
) -> dict:
    lead = await session.get(Lead, payload.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    signal = IntentSignal(
        lead_id=payload.lead_id,
        company_domain=lead.company_domain,
        company_name=lead.company_name,
        signal_type=payload.signal_type,
        source=payload.source,
        score=payload.score,
    )
    session.add(signal)
    await session.commit()
    return {"id": str(signal.id), "lead_id": str(payload.lead_id), "signal_type": payload.signal_type}
