import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    scraping = "scraping"
    enriching = "enriching"
    scoring = "scoring"
    completed = "completed"
    failed = "failed"


class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    query: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    max_results: Mapped[int] = mapped_column(Integer, default=40)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    sources_enabled: Mapped[list[str]] = mapped_column(JSON, default=list)

    status: Mapped[JobStatus] = mapped_column(SqlEnum(JobStatus, name="job_status"), default=JobStatus.pending)
    total_sources: Mapped[int] = mapped_column(Integer, default=0)
    completed_sources: Mapped[int] = mapped_column(Integer, default=0)
    current_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    status_message: Mapped[str | None] = mapped_column(String(255), nullable=True)

    total_raw_leads: Mapped[int] = mapped_column(Integer, default=0)
    total_after_dedup: Mapped[int] = mapped_column(Integer, default=0)
    total_enriched: Mapped[int] = mapped_column(Integer, default=0)
    total_verified_emails: Mapped[int] = mapped_column(Integer, default=0)
    total_final_leads: Mapped[int] = mapped_column(Integer, default=0)
    total_results: Mapped[int] = mapped_column(Integer, default=0)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    errors: Mapped[list[dict]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    leads: Mapped[list["Lead"]] = relationship(back_populates="job", cascade="all, delete-orphan")


GenerationJob = ScrapeJob
