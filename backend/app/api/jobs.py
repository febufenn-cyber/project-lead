from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import GenerationJob, Lead
from app.schemas import JobCreateRequest, JobResponse, LeadListResponse, LeadResponse
from app.services.generator import run_generation_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobResponse)
async def create_job(
    payload: JobCreateRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
) -> GenerationJob:
    job = GenerationJob(
        query=payload.query,
        location=payload.location,
        industry=None,
        max_results=payload.max_results,
        sources_enabled=payload.sources_enabled or ["google_maps"],
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    background_tasks.add_task(run_generation_job, job.id)
    return job


@router.get("", response_model=list[JobResponse])
async def list_jobs(
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> list[GenerationJob]:
    result = await session.execute(select(GenerationJob).order_by(GenerationJob.created_at.desc()).offset(offset).limit(limit))
    return list(result.scalars().all())


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: UUID, session: AsyncSession = Depends(get_db)) -> GenerationJob:
    job = await session.get(GenerationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}/leads", response_model=LeadListResponse)
async def get_job_leads(
    job_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> LeadListResponse:
    job = await session.get(GenerationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    total = await session.scalar(select(func.count()).select_from(Lead).where(Lead.job_id == job_id))
    result = await session.execute(
        select(Lead)
        .where(Lead.job_id == job_id)
        .order_by(Lead.lead_score.desc(), Lead.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    items = [LeadResponse.model_validate(lead) for lead in result.scalars().all()]
    return LeadListResponse(total=total or 0, items=items)
