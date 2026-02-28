import asyncio
from uuid import UUID

from workers.celery_app import celery_app
from app.services.generator import run_generation_job


@celery_app.task(name="leadgen.run_generation_job")
def run_generation_job_task(job_id: str) -> None:
    asyncio.run(run_generation_job(UUID(job_id)))
