"""
TaxChunk — SQLAlchemy ORM Model for pgvector Tax Knowledge Base.

Table: tax_chunks
    id            UUID PK            — auto-generated
    chunk_id      TEXT UNIQUE        — "{source_stem}::{index:04d}" (for upsert)
    document_name TEXT               — human-readable law name (Arabic)
    law_number    TEXT               — "القانون رقم 67 لسنة 2016"
    article       TEXT               — "مادة 3" — used for legal citation in response
    section       TEXT               — current chapter/section title
    chunk_text    TEXT NOT NULL      — normalized Arabic chunk content
    embedding     VECTOR(1536)       — text-embedding-3-small (1536 dims)
    metadata_     JSONB              — extra fields: source_file, char_count, etc.
    created_at    TIMESTAMPTZ        — auto set by DB server

Dependency:
    pip install pgvector          — provides Vector type for SQLAlchemy
    pgvector extension enabled    — done in Sprint 0 DB setup
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TaxChunk(Base):
    __tablename__ = "tax_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    chunk_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        unique=True,
        index=True,
    )
    document_name: Mapped[str] = mapped_column(Text, nullable=False, default="")
    law_number:    Mapped[str] = mapped_column(Text, nullable=False, default="")
    article:       Mapped[str] = mapped_column(Text, nullable=False, default="")
    section:       Mapped[str] = mapped_column(Text, nullable=False, default="")
    chunk_text:    Mapped[str] = mapped_column(Text, nullable=False)

    # pgvector column — 1536 dims matches text-embedding-3-small
    embedding: Mapped[list[float]] = mapped_column(
        Vector(1536),
        nullable=False,
    )

    # JSONB for flexible extra metadata (source_file, char_count, etc.)
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<TaxChunk id={self.chunk_id!r} article={self.article!r}>"
