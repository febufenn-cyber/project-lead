"""API routes for AI-powered lead enrichment via Gemini / Vertex AI."""

import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import GenerationJob, Lead
from app.services.claude_enrichment import (
    INDIA_INDUSTRY_CONTEXT,
    batch_enrich_leads,
    enrich_lead,
    estimate_enrichment_cost,
)
from app.services.scoring_enhanced import score_enriched_lead

logger = logging.getLogger(__name__)

router = APIRouter(tags=["enrichment"])


# ---------------------------------------------------------------------------
# POST /leads/{lead_id}/enrich
# ---------------------------------------------------------------------------

@router.post("/leads/{lead_id}/enrich")
async def enrich_single_lead(
    lead_id: UUID,
    industry_hint: str | None = Query(default=None, description="Industry key, e.g. bfsi, it_services"),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Enrich a single lead with Gemini AI analysis and persist results."""
    lead = await session.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead_dict = {
        "company_name": lead.company_name,
        "company_website": lead.company_website,
        "city": lead.city,
        "state": lead.state,
        "country": lead.country,
        "company_phone": lead.company_phone,
        "rating": lead.rating,
        "review_count": lead.review_count,
    }

    logger.info("Enriching lead %s (%s)", lead_id, lead.company_name)
    enrichment = await enrich_lead(lead_dict, industry_hint=industry_hint)

    lead.ai_enrichment = enrichment
    lead.is_enriched = True

    # Re-score with AI bonus
    scoring = score_enriched_lead(
        rating=lead.rating,
        review_count=lead.review_count,
        website=lead.company_website,
        phone=lead.company_phone,
        address=lead.address,
        ai_enrichment=enrichment,
    )
    lead.lead_score = scoring["total_score"]

    await session.commit()
    await session.refresh(lead)

    return {
        "lead_id": str(lead_id),
        "company_name": lead.company_name,
        "ai_enrichment": enrichment,
        "scoring": scoring,
    }


# ---------------------------------------------------------------------------
# POST /jobs/{job_id}/enrich  (background batch)
# ---------------------------------------------------------------------------

async def _batch_enrich_job(job_id: UUID, industry_hint: str | None) -> None:
    """Background task: enrich all leads for a job."""
    from app.database import AsyncSessionFactory

    async with AsyncSessionFactory() as session:
        job = await session.get(GenerationJob, job_id)
        if not job:
            logger.error("Batch enrich: job %s not found", job_id)
            return

        result = await session.execute(select(Lead).where(Lead.job_id == job_id))
        leads = list(result.scalars().all())

        if not leads:
            logger.info("Batch enrich: no leads found for job %s", job_id)
            return

        logger.info("Batch enriching %d leads for job %s", len(leads), job_id)
        lead_dicts = [
            {
                "company_name": l.company_name,
                "company_website": l.company_website,
                "city": l.city,
                "state": l.state,
                "country": l.country,
                "company_phone": l.company_phone,
                "rating": l.rating,
                "review_count": l.review_count,
            }
            for l in leads
        ]

        enrichments = await batch_enrich_leads(lead_dicts, industry_hint=industry_hint)

        for lead, enrichment in zip(leads, enrichments):
            lead.ai_enrichment = enrichment
            lead.is_enriched = True
            scoring = score_enriched_lead(
                rating=lead.rating,
                review_count=lead.review_count,
                website=lead.company_website,
                phone=lead.company_phone,
                address=lead.address,
                ai_enrichment=enrichment,
            )
            lead.lead_score = scoring["total_score"]

        await session.commit()
        logger.info("Batch enrich complete for job %s", job_id)


@router.post("/jobs/{job_id}/enrich")
async def enrich_job_leads(
    job_id: UUID,
    background_tasks: BackgroundTasks,
    industry_hint: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Queue AI enrichment for all leads belonging to a job (runs in background)."""
    job = await session.get(GenerationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    total = await session.scalar(
        select(func.count()).select_from(Lead).where(Lead.job_id == job_id)
    ) or 0

    background_tasks.add_task(_batch_enrich_job, job_id, industry_hint)

    return {
        "job_id": str(job_id),
        "message": "Enrichment queued",
        "leads_to_enrich": total,
        "estimated_cost": estimate_enrichment_cost(total),
    }


# ---------------------------------------------------------------------------
# GET /enrichment/cost-estimate
# ---------------------------------------------------------------------------

@router.get("/enrichment/cost-estimate")
async def cost_estimate(
    lead_count: int = Query(default=10, ge=1, le=10_000, description="Number of leads to estimate cost for"),
) -> dict:
    """Return approximate Gemini API cost for enriching *lead_count* leads."""
    return estimate_enrichment_cost(lead_count)


# ---------------------------------------------------------------------------
# GET /enrichment/industries
# ---------------------------------------------------------------------------

@router.get("/enrichment/industries")
async def list_industries() -> dict:
    """List all supported industry verticals with their AI use-cases."""
    return {
        key: {
            "sector": ctx["sector"],
            "ai_use_cases": ctx["ai_use_cases"],
            "typical_buyers": ctx["typical_buyers"],
            "budget_range": ctx["budget_range"],
        }
        for key, ctx in INDIA_INDUSTRY_CONTEXT.items()
    }
