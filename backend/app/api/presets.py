"""API routes for India enterprise lead-generation presets."""

import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.data.india_presets import INDIA_PRESETS, PRESETS_BY_ID
from app.models import GenerationJob
from app.services.generator import run_generation_job

logger = logging.getLogger(__name__)

router = APIRouter(tags=["presets"])


# ---------------------------------------------------------------------------
# GET /presets/india
# ---------------------------------------------------------------------------

@router.get("/presets/india")
async def list_india_presets(
    industry: str | None = Query(default=None, description="Filter by industry key, e.g. bfsi, it_services"),
) -> list[dict]:
    """Return all India enterprise presets, optionally filtered by industry."""
    presets = INDIA_PRESETS
    if industry:
        presets = [p for p in presets if p.get("industry", "").lower() == industry.lower()]
    return presets


# ---------------------------------------------------------------------------
# GET /presets/india/{preset_id}
# ---------------------------------------------------------------------------

@router.get("/presets/india/{preset_id}")
async def get_india_preset(preset_id: str) -> dict:
    """Return a specific India preset by its ID."""
    preset = PRESETS_BY_ID.get(preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_id}' not found")
    return preset


# ---------------------------------------------------------------------------
# POST /jobs/preset/{preset_id}
# ---------------------------------------------------------------------------

@router.post("/jobs/preset/{preset_id}")
async def create_job_from_preset(
    preset_id: str,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Create a scrape job pre-configured from an India enterprise preset."""
    preset = PRESETS_BY_ID.get(preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_id}' not found")

    job = GenerationJob(
        query=preset["query"],
        location=preset["location"],
        industry=preset.get("industry"),
        max_results=preset.get("max_results", 50),
        sources_enabled=["google_maps"],
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    background_tasks.add_task(run_generation_job, job.id)

    logger.info("Created job %s from preset '%s'", job.id, preset_id)
    return {
        "job_id": str(job.id),
        "preset_id": preset_id,
        "preset_name": preset["name"],
        "query": job.query,
        "location": job.location,
        "max_results": job.max_results,
        "status": job.status,
    }
