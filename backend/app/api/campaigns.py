"""Campaigns API - create, manage, send sequences."""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Campaign, CampaignRecipient, CampaignStatus, CampaignStep, EmailAccount, EmailEvent, Lead
from app.services.campaign_service import send_campaign_step

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    from_email: str | None = None
    from_name: str | None = None
    reply_to: str | None = None
    email_account_id: UUID | None = None


class CampaignStepCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=500)
    body_html: str | None = None
    body_text: str | None = None
    delay_days: int = Field(default=0, ge=0)
    order: int = Field(default=0, ge=0)


class AddRecipientsRequest(BaseModel):
    lead_ids: list[UUID] = Field(max_length=500)


@router.post("", response_model=dict)
async def create_campaign(
    payload: CampaignCreate,
    session: AsyncSession = Depends(get_db),
) -> dict:
    campaign = Campaign(
        name=payload.name,
        status=CampaignStatus.draft,
        from_email=payload.from_email,
        from_name=payload.from_name,
        reply_to=payload.reply_to,
        email_account_id=payload.email_account_id,
    )
    session.add(campaign)
    await session.commit()
    await session.refresh(campaign)
    return {"id": str(campaign.id), "name": campaign.name, "status": campaign.status.value}


@router.get("", response_model=list)
async def list_campaigns(
    session: AsyncSession = Depends(get_db),
) -> list:
    result = await session.execute(
        select(Campaign).order_by(Campaign.created_at.desc())
    )
    campaigns = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "status": c.status.value,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in campaigns
    ]


@router.get("/{campaign_id}", response_model=dict)
async def get_campaign(
    campaign_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> dict:
    campaign = await session.get(Campaign, campaign_id, options=[selectinload(Campaign.steps), selectinload(Campaign.recipients)])
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {
        "id": str(campaign.id),
        "name": campaign.name,
        "status": campaign.status.value,
        "from_email": campaign.from_email,
        "from_name": campaign.from_name,
        "steps": [{"id": str(s.id), "subject": s.subject, "order": s.order, "delay_days": s.delay_days} for s in campaign.steps],
        "recipients_count": len(campaign.recipients),
    }


@router.post("/{campaign_id}/steps")
async def add_step(
    campaign_id: UUID,
    payload: CampaignStepCreate,
    session: AsyncSession = Depends(get_db),
) -> dict:
    campaign = await session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    step = CampaignStep(
        campaign_id=campaign_id,
        subject=payload.subject,
        body_html=payload.body_html,
        body_text=payload.body_text,
        delay_days=payload.delay_days,
        order=payload.order,
    )
    session.add(step)
    await session.commit()
    await session.refresh(step)
    return {"id": str(step.id), "subject": step.subject, "order": step.order}


@router.post("/{campaign_id}/recipients")
async def add_recipients(
    campaign_id: UUID,
    payload: AddRecipientsRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    campaign = await session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    added = 0
    for lead_id in payload.lead_ids:
        lead = await session.get(Lead, lead_id)
        if not lead:
            continue
        email = lead.contact_email or lead.company_email
        if not email:
            continue
        existing = await session.scalar(
            select(CampaignRecipient).where(
                CampaignRecipient.campaign_id == campaign_id,
                CampaignRecipient.email == email,
            )
        )
        if existing:
            continue
        rec = CampaignRecipient(
            campaign_id=campaign_id,
            lead_id=lead_id,
            email=email,
            first_name=lead.contact_first_name,
            last_name=lead.contact_last_name,
            company_name=lead.company_name,
        )
        session.add(rec)
        added += 1
    await session.commit()
    return {"added": added, "total_requested": len(payload.lead_ids)}


@router.post("/{campaign_id}/start")
async def start_campaign(
    campaign_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
) -> dict:
    campaign = await session.get(Campaign, campaign_id, options=[selectinload(Campaign.steps), selectinload(Campaign.recipients)])
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if not campaign.steps:
        raise HTTPException(status_code=400, detail="Add at least one step")
    if not campaign.recipients:
        raise HTTPException(status_code=400, detail="Add at least one recipient")
    campaign.status = CampaignStatus.active
    await session.commit()
    for rec in campaign.recipients:
        if rec.status == "pending" and rec.current_step < len(campaign.steps):
            background_tasks.add_task(send_campaign_step, campaign_id, rec.id)
    return {"status": "active", "message": "Campaign started"}


@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> dict:
    campaign = await session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign.status = CampaignStatus.paused
    await session.commit()
    return {"status": "paused"}


@router.get("/{campaign_id}/stats")
async def campaign_stats(
    campaign_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> dict:
    campaign = await session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    sent = await session.scalar(
        select(func.count()).select_from(CampaignRecipient).where(
            CampaignRecipient.campaign_id == campaign_id,
            CampaignRecipient.status == "sent",
        )
    )
    total = await session.scalar(
        select(func.count()).select_from(CampaignRecipient).where(
            CampaignRecipient.campaign_id == campaign_id,
        )
    )
    opened = await session.scalar(
        select(func.count()).select_from(EmailEvent).where(
            EmailEvent.campaign_id == campaign_id,
            EmailEvent.event_type == "opened",
        )
    )
    clicked = await session.scalar(
        select(func.count()).select_from(EmailEvent).where(
            EmailEvent.campaign_id == campaign_id,
            EmailEvent.event_type == "clicked",
        )
    )
    replied = await session.scalar(
        select(func.count()).select_from(EmailEvent).where(
            EmailEvent.campaign_id == campaign_id,
            EmailEvent.event_type == "replied",
        )
    )
    return {
        "total_recipients": total or 0,
        "sent": sent or 0,
        "opened": opened or 0,
        "clicked": clicked or 0,
        "replied": replied or 0,
    }
