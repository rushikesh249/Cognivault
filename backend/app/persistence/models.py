"""SQLAlchemy ORM models for SQLite persistence (TRD Section 10)."""

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
    """Tasks table (TRD Section 10.1, Table 21)."""
    __tablename__ = "tasks"

    task_id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    task_type = Column(String(32), nullable=False)
    prompt = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="created")
    model_used = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    events = relationship("TaskEventORM", back_populates="task", cascade="all, delete-orphan")
    files = relationship("FileORM", back_populates="task", cascade="all, delete-orphan")
    artifacts = relationship("ArtifactORM", back_populates="task", cascade="all, delete-orphan")


class TaskEventORM(Base):
    """Task events table (TRD Section 10.2, Table 22)."""
    __tablename__ = "task_events"

    event_id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=False, index=True)
    node = Column(String(64), nullable=False)
    message = Column(Text, nullable=False)
    level = Column(String(16), nullable=False, default="info")
    ts = Column(DateTime, default=get_utc_now, nullable=False)

    task = relationship("TaskORM", back_populates="events")


class FileORM(Base):
    """Uploaded files table (TRD Section 10.3, Table 23)."""
    __tablename__ = "files"

    file_id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.task_id", ondelete="SET NULL"), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    mime_type = Column(String(128), nullable=False)
    pages = Column(Integer, nullable=True)
    size_bytes = Column(Integer, nullable=False)
    storage_path = Column(String(512), nullable=False)
    uploaded_at = Column(DateTime, default=get_utc_now, nullable=False)

    task = relationship("TaskORM", back_populates="files")


class KnowledgeDocumentORM(Base):
    """Knowledge Base Documents metadata table (TRD Section 10.4, Table 24)."""
    __tablename__ = "knowledge_documents"

    doc_id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    category = Column(String(32), nullable=False)  # CHECK IN (sop, manual, guideline, standard, approval_note)
    source_path = Column(String(512), nullable=False)
    indexed_at = Column(DateTime, nullable=True)
    chunk_count = Column(Integer, nullable=False, default=0)


class ArtifactORM(Base):
    """Generated artifacts metadata table (TRD Section 10.5, Table 25)."""
    __tablename__ = "artifacts"

    artifact_id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(32), nullable=False)  # CHECK IN ('docx', 'xlsx', 'pptx', 'pdf', 'code')
    title = Column(String(255), nullable=False)
    storage_path = Column(String(512), nullable=False)
    sources_json = Column(Text, nullable=False, default="[]")  # JSON list of citations
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    task = relationship("TaskORM", back_populates="artifacts")


class ModelRegistryMetaORM(Base):
    """Model Registry availability cache table (TRD Section 10.6, Table 26, ADR-003)."""
    __tablename__ = "model_registry_meta"

    model_id = Column(String(128), primary_key=True)
    role = Column(String(32), nullable=False)
    display_name = Column(String(255), nullable=True)
    vram_gb = Column(Float, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    last_probe_at = Column(DateTime, nullable=True)
    last_available = Column(Boolean, nullable=True)
