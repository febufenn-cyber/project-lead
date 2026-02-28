from uuid import UUID

from app.orchestrator.pipeline import PipelineManager
from app.orchestrator.task_manager import TaskManager


class OrchestratorEngine:
    def __init__(self, pipeline: PipelineManager | None = None, task_manager: TaskManager | None = None):
        self.pipeline = pipeline or PipelineManager()
        self.task_manager = task_manager or TaskManager()

    async def run_job(self, job_id: UUID) -> None:
        await self.task_manager.enqueue_generation(job_id)
