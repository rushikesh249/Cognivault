"""SQLAlchemy ORM models for SQLite persistence (TRD §10)."""

import datetime
import uuid
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.app.persistence.db import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def get_utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class TaskORM(Base):
    """Tasks table (TRD §10.1, Table 21)."""
    __tablename__ = "tasks"

    task_id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    task_type = Column(String(32), nullable=False)  # CHECK IN (document, coding, vision)
    prompt = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="created")  # CHECK IN (created, running, succeeded, failed, failed_bounded)
    model_used = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    events = relationship("TaskEventORM", back_populates="task", cascade="all, delete-orphan")


class TaskEventORM(Base):
    """Task events table (TRD §10.2, Table 22)."""
    __tablename__ = "task_events"

    event_id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=False, index=True)
    node = Column(String(64), nullable=False)
    message = Column(Text, nullable=False)
    level = Column(String(16), nullable=False, default="info")  # CHECK IN (info, warn, error)
    ts = Column(DateTime, default=get_utc_now, nullable=False)

    task = relationship("TaskORM", back_populates="events")


class ModelRegistryMetaORM(Base):
    """Model Registry availability cache table (TRD §10.6, Table 26, ADR-003)."""
    __tablename__ = "model_registry_meta"

    model_id = Column(String(128), primary_key=True)
    role = Column(String(32), nullable=False)  # CHECK IN (general, coding, vision)
    display_name = Column(String(255), nullable=True)
    vram_gb = Column(Float, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    last_probe_at = Column(DateTime, nullable=True)
    last_available = Column(Boolean, nullable=True)
