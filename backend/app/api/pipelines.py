"""Pipelines and deals CRM API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Deal, Lead, Pipeline, PipelineStage

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


class PipelineCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class StageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    order: int = Field(default=0, ge=0)
    is_won: bool = False
    is_lost: bool = False


class DealCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    lead_id: UUID | None = None
    value: float | None = None
    currency: str = "USD"
    notes: str | None = None


@router.post("", response_model=dict)
async def create_pipeline(
    payload: PipelineCreate,
    session: AsyncSession = Depends(get_db),
) -> dict:
    pipeline = Pipeline(
        name=payload.name,
        description=payload.description,
    )
    session.add(pipeline)
    await session.commit()
    await session.refresh(pipeline)
    default_stages = ["New", "Contacted", "Qualified", "Proposal", "Won", "Lost"]
    for i, name in enumerate(default_stages):
        stage = PipelineStage(
            pipeline_id=pipeline.id,
            name=name,
            order=i,
            is_won=(name == "Won"),
            is_lost=(name == "Lost"),
        )
        session.add(stage)
    await session.commit()
    return {"id": str(pipeline.id), "name": pipeline.name}


@router.get("", response_model=list)
async def list_pipelines(session: AsyncSession = Depends(get_db)) -> list:
    result = await session.execute(
        select(Pipeline).order_by(Pipeline.created_at.desc())
    )
    pipelines = result.scalars().all()
    return [{"id": str(p.id), "name": p.name} for p in pipelines]


@router.get("/{pipeline_id}", response_model=dict)
async def get_pipeline(
    pipeline_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> dict:
    pipeline = await session.get(
        Pipeline, pipeline_id,
        options=[selectinload(Pipeline.stages), selectinload(Pipeline.deals)],
    )
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return {
        "id": str(pipeline.id),
        "name": pipeline.name,
        "stages": [
            {"id": str(s.id), "name": s.name, "order": s.order, "deals_count": len([d for d in pipeline.deals if d.stage_id == s.id])}
            for s in sorted(pipeline.stages, key=lambda x: x.order)
        ],
    }


@router.post("/{pipeline_id}/stages")
async def add_stage(
    pipeline_id: UUID,
    payload: StageCreate,
    session: AsyncSession = Depends(get_db),
) -> dict:
    pipeline = await session.get(Pipeline, pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    stage = PipelineStage(
        pipeline_id=pipeline_id,
        name=payload.name,
        order=payload.order,
        is_won=payload.is_won,
        is_lost=payload.is_lost,
    )
    session.add(stage)
    await session.commit()
    await session.refresh(stage)
    return {"id": str(stage.id), "name": stage.name, "order": stage.order}


@router.get("/deals/{deal_id}")
async def get_deal(
    deal_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> dict:
    deal = await session.get(Deal, deal_id, options=[selectinload(Deal.lead), selectinload(Deal.stage)])
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return {
        "id": str(deal.id),
        "name": deal.name,
        "value": float(deal.value) if deal.value else None,
        "currency": deal.currency,
        "stage": {"id": str(deal.stage.id), "name": deal.stage.name} if deal.stage else None,
        "lead_id": str(deal.lead_id) if deal.lead_id else None,
    }


@router.post("/{pipeline_id}/deals")
async def create_deal(
    pipeline_id: UUID,
    payload: DealCreate,
    session: AsyncSession = Depends(get_db),
) -> dict:
    pipeline = await session.get(Pipeline, pipeline_id, options=[selectinload(Pipeline.stages)])
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    first_stage = next((s for s in sorted(pipeline.stages, key=lambda x: x.order)), None)
    if not first_stage:
        raise HTTPException(status_code=400, detail="Pipeline has no stages")
    deal = Deal(
        pipeline_id=pipeline_id,
        stage_id=first_stage.id,
        lead_id=payload.lead_id,
        name=payload.name,
        value=payload.value,
        currency=payload.currency,
        notes=payload.notes,
    )
    session.add(deal)
    await session.commit()
    await session.refresh(deal)
    return {"id": str(deal.id), "name": deal.name, "stage_id": str(deal.stage_id)}


@router.post("/deals/{deal_id}/attach-lead/{lead_id}")
async def attach_lead_to_deal(
    deal_id: UUID,
    lead_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> dict:
    deal = await session.get(Deal, deal_id)
    lead = await session.get(Lead, lead_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    deal.lead_id = lead_id
    await session.commit()
    return {"status": "ok", "deal_id": str(deal_id), "lead_id": str(lead_id)}


@router.patch("/deals/{deal_id}/stage/{stage_id}")
async def move_deal_stage(
    deal_id: UUID,
    stage_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> dict:
    deal = await session.get(Deal, deal_id)
    stage = await session.get(PipelineStage, stage_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    if not stage or stage.pipeline_id != deal.pipeline_id:
        raise HTTPException(status_code=404, detail="Stage not found")
    deal.stage_id = stage_id
    if stage.is_won or stage.is_lost:
        from datetime import datetime
        deal.closed_at = datetime.utcnow()
    await session.commit()
    return {"status": "ok", "deal_id": str(deal_id), "stage_id": str(stage_id)}
