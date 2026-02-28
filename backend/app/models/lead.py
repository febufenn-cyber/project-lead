import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (UniqueConstraint("source", "external_id", "job_id", name="uq_source_external_per_job"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scrape_jobs.id", ondelete="CASCADE"))

    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    company_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    company_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    street: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    zip_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    contact_first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contact_last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contact_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contact_linkedin: Mapped[str | None] = mapped_column(String(500), nullable=True)

    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    lead_score: Mapped[int] = mapped_column(Integer, default=0)
    intent_score: Mapped[int] = mapped_column(Integer, default=0)

    source: Mapped[str] = mapped_column(String(64), default="google_places")
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    data_sources: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_urls: Mapped[list[str]] = mapped_column(JSON, default=list)

    email_found: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_enriched: Mapped[bool] = mapped_column(Boolean, default=False)

    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    job: Mapped["ScrapeJob"] = relationship(back_populates="leads")

    @property
    def business_name(self) -> str:
        return self.company_name

    @property
    def website(self) -> str | None:
        return self.company_website

    @property
    def phone(self) -> str | None:
        return self.company_phone

    @property
    def email(self) -> str | None:
        return self.contact_email or self.company_email

    @property
    def address(self) -> str | None:
        parts = [self.street, self.city, self.state, self.country]
        joined = ", ".join([p for p in parts if p])
        return joined or None

    @property
    def postal_code(self) -> str | None:
        return self.zip_code

    @property
    def raw_payload(self) -> dict:
        return self.raw_data
