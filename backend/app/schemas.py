from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import JobStatus


class JobCreateRequest(BaseModel):
    query: str = Field(min_length=2, max_length=255)
    location: str = Field(min_length=2, max_length=255)
    max_results: int = Field(default=40, ge=1, le=200)
    sources_enabled: list[str] = Field(
        default_factory=lambda: ["google_maps"],
        description="Data sources: google_maps, google_search, yellow_pages",
    )


class JobResponse(BaseModel):
    id: UUID
    query: str
    location: str
    max_results: int
    status: JobStatus
    total_results: int
    error_message: str | None
    sources_enabled: list[str] | None = None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class LeadResponse(BaseModel):
    id: UUID
    job_id: UUID
    source: str
    external_id: str | None
    business_name: str
    website: str | None
    phone: str | None
    email: str | None
    address: str | None
    city: str | None
    state: str | None
    country: str | None
    postal_code: str | None
    latitude: float | None
    longitude: float | None
    rating: float | None
    review_count: int | None
    lead_score: int
    created_at: datetime

    model_config = {"from_attributes": True}


class LeadListResponse(BaseModel):
    total: int
    items: list[LeadResponse]
