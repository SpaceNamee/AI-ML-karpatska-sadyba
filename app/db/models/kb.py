"""Knowledge-base models: documents the host uploads, their ingestion job, and
the text chunks (with embeddings) produced from them.

Follows the patterns in `cottage.py` / `bedroom.py`.
"""

import enum
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base, TimestampMixin, TZDateTime, pg_enum


class IngestionStatus(enum.StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class KbDocument(TimestampMixin, Base):
    __tablename__ = "kb_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    original_filename: Mapped[str] = mapped_column(String(255))
    # The one genuinely unique field: where the file lives in the volume.
    stored_path: Mapped[str] = mapped_column(String(500), unique=True)
    content_type: Mapped[str] = mapped_column(String(100))

    job: Mapped["IngestionJob | None"] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    chunks: Mapped[list["KbChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="KbChunk.position",
    )


class IngestionJob(TimestampMixin, Base):
    """One row per document (shared primary key with `kb_documents`).

    Deliberately 1:1, not a history table: re-uploading a corrected file
    overwrites this row. "This document failed twice then succeeded" is not a
    question the sprint needs; revisit if it ever becomes one.
    """

    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        CheckConstraint("chunk_count >= 0", name="ck_ingestion_jobs_chunk_count_non_negative"),
    )

    document_id: Mapped[int] = mapped_column(
        ForeignKey("kb_documents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    status: Mapped[IngestionStatus] = mapped_column(
        pg_enum(IngestionStatus),
        default=IngestionStatus.PENDING,
        server_default=IngestionStatus.PENDING.value,
    )
    error: Mapped[str | None] = mapped_column(Text)
    chunk_count: Mapped[int] = mapped_column(server_default=text("0"))
    started_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    finished_at: Mapped[datetime | None] = mapped_column(TZDateTime)

    document: Mapped[KbDocument] = relationship(back_populates="job")


class KbChunk(Base):
    """A text fragment of a document. Immutable — a re-ingest deletes and rebuilds
    the whole set — so no timestamp mixin.
    """

    __tablename__ = "kb_chunks"
    __table_args__ = (CheckConstraint("position >= 0", name="ck_kb_chunks_position_non_negative"),)

    # Composite PK: `position` is unique within a document, and `document_id` as
    # the leading column is the index for "all chunks of document X" for free.
    document_id: Mapped[int] = mapped_column(
        ForeignKey("kb_documents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(primary_key=True)

    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int | None]
    # NULL until the embedding pass runs. "Has this been processed?" is answered
    # by IngestionJob.status, never by inspecting this column.
    embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.embedding_dimensions))
    # Attribute is `meta` because `metadata` is reserved on the declarative Base;
    # the database column is still named "metadata".
    meta: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    document: Mapped[KbDocument] = relationship(back_populates="chunks")
