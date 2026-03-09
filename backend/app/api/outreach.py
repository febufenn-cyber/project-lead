"""API routes for AI-powered outreach generation."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Lead
from app.services.outreach_generator import generate_outreach

logger = logging.getLogger(__name__)

router = APIRouter(tags=["outreach"])


class OutreachParams(BaseModel):
    sender_name: str = Field(default="Sales Team", max_length=100)
    sender_title: str = Field(default="Business Development Manager", max_length=100)
    tone: str = Field(default="consultative", description="formal | conversational | consultative")
    language: str = Field(default="english", description="english | hindi_english")


# ---------------------------------------------------------------------------
# POST /leads/{lead_id}/outreach
# ---------------------------------------------------------------------------

@router.post("/leads/{lead_id}/outreach")
async def generate_lead_outreach(
    lead_id: UUID,
    params: OutreachParams,
    save: bool = Query(default=True, description="Persist generated outreach to the lead record"),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Generate personalised outreach copy for a lead, optionally saving to DB."""
    lead = await session.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead_dict = {
        "company_name": lead.company_name,
        "company_website": lead.company_website,
        "city": lead.city,
        "state": lead.state,
        "country": lead.country,
        "ai_enrichment": lead.ai_enrichment,
    }

    logger.info("Generating outreach for lead %s (%s)", lead_id, lead.company_name)
    outreach = await generate_outreach(
        lead_dict,
        sender_name=params.sender_name,
        sender_title=params.sender_title,
        tone=params.tone,
        language=params.language,
    )

    if save:
        lead.outreach_data = outreach
        await session.commit()

    return {
        "lead_id": str(lead_id),
        "company_name": lead.company_name,
        "outreach": outreach,
    }


# ---------------------------------------------------------------------------
# POST /leads/{lead_id}/outreach/regenerate
# ---------------------------------------------------------------------------

@router.post("/leads/{lead_id}/outreach/regenerate")
async def regenerate_lead_outreach(
    lead_id: UUID,
    params: OutreachParams,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Regenerate outreach with (optionally different) parameters and overwrite saved data."""
    lead = await session.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead_dict = {
        "company_name": lead.company_name,
        "company_website": lead.company_website,
        "city": lead.city,
        "state": lead.state,
        "country": lead.country,
        "ai_enrichment": lead.ai_enrichment,
    }

    logger.info("Regenerating outreach for lead %s (%s)", lead_id, lead.company_name)
    outreach = await generate_outreach(
        lead_dict,
        sender_name=params.sender_name,
        sender_title=params.sender_title,
        tone=params.tone,
        language=params.language,
    )

    lead.outreach_data = outreach
    await session.commit()

    return {
        "lead_id": str(lead_id),
        "company_name": lead.company_name,
        "outreach": outreach,
        "regenerated": True,
    }
