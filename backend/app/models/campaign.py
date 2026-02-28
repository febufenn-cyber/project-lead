"""Campaign and email event models."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CampaignStatus(str, Enum):
    draft = "draft"
    active = "active"
    paused = "paused"
    completed = "completed"


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[CampaignStatus] = mapped_column(SqlEnum(CampaignStatus), default=CampaignStatus.draft)

    email_account_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("email_accounts.id"), nullable=True)
    from_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    from_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reply_to: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    steps: Mapped[list["CampaignStep"]] = relationship(back_populates="campaign", cascade="all, delete-orphan", order_by="CampaignStep.order")
    recipients: Mapped[list["CampaignRecipient"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")


class CampaignStep(Base):
    __tablename__ = "campaign_steps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"))

    order: Mapped[int] = mapped_column(Integer, default=0)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    delay_days: Mapped[int] = mapped_column(Integer, default=0)

    campaign: Mapped["Campaign"] = relationship(back_populates="steps")


class CampaignRecipient(Base):
    __tablename__ = "campaign_recipients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"))
    lead_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True)

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    current_step: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, sent, opened, clicked, replied, bounced, unsubscribed
    last_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    campaign: Mapped["Campaign"] = relationship(back_populates="recipients")


class EmailEventType(str, Enum):
    sent = "sent"
    delivered = "delivered"
    opened = "opened"
    clicked = "clicked"
    replied = "replied"
    bounced = "bounced"
    unsubscribed = "unsubscribed"


class EmailEvent(Base):
    __tablename__ = "email_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"))
    recipient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaign_recipients.id", ondelete="CASCADE"))

    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict | None] = mapped_column(default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
