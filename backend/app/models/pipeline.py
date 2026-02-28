"""Pipeline and deal models for CRM."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Pipeline(Base):
    __tablename__ = "pipelines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    stages: Mapped[list["PipelineStage"]] = relationship(back_populates="pipeline", cascade="all, delete-orphan", order_by="PipelineStage.order")
    deals: Mapped[list["Deal"]] = relationship(back_populates="pipeline", cascade="all, delete-orphan")


class PipelineStage(Base):
    __tablename__ = "pipeline_stages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pipelines.id", ondelete="CASCADE"))

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0)
    is_won: Mapped[bool] = mapped_column(Boolean, default=False)
    is_lost: Mapped[bool] = mapped_column(Boolean, default=False)

    pipeline: Mapped["Pipeline"] = relationship(back_populates="stages")
    deals: Mapped[list["Deal"]] = relationship(back_populates="stage", cascade="all, delete-orphan")


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pipelines.id", ondelete="CASCADE"))
    stage_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pipeline_stages.id", ondelete="CASCADE"))
    lead_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), default="USD")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    pipeline: Mapped["Pipeline"] = relationship(back_populates="deals")
    stage: Mapped["PipelineStage"] = relationship(back_populates="deals")
