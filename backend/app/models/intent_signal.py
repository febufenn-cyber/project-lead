"""Intent signals for lead/company intent scoring."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IntentSignal(Base):
    __tablename__ = "intent_signals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True)
    company_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    signal_type: Mapped[str] = mapped_column(String(64), nullable=False)  # job_posting, funding, tech_change, website_visit
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, default=dict)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
