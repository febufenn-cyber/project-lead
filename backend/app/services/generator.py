"""Lead generation job runner - delegates to orchestrator pipeline."""

from app.orchestrator.task_manager import run_generation_job

__all__ = ["run_generation_job"]
