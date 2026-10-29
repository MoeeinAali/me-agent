"""Database schema. ``data/record.json`` stays the source of truth; these tables are derived from
it (entities, chunks) or record what happened (conversations, traces, gaps, evals)."""

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    Computed,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

EMBED_DIM = 1536  # text-embedding-3-small; changing the model needs a re-embed migration

GapStatus = Literal["open", "resolved", "ignored"]


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSONB, datetime: DateTime(timezone=True)}  # noqa: RUF012


class Entity(Base):
    """One record item (a project, a course, a book, ...) addressable by its path."""

    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # "<kind>:<record id>"
    kind: Mapped[str] = mapped_column(String, index=True)
    path: Mapped[str] = mapped_column(String, unique=True)  # e.g. projects[comeback]
    name: Mapped[str] = mapped_column(Text)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    data: Mapped[dict[str, Any]]
    content_hash: Mapped[str] = mapped_column(String(64))
    name_embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBED_DIM), nullable=True)

    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="entity", cascade="all, delete-orphan", passive_deletes=True
    )


class Chunk(Base):
    """A retrievable piece of text with its field path, embedding, and lexical index."""

    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # the chunk's path
    entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    path: Mapped[str] = mapped_column(String)
    text: Mapped[str] = mapped_column(Text)
    lang: Mapped[str] = mapped_column(String(2), default="en")
    content_hash: Mapped[str] = mapped_column(String(64))
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBED_DIM))
    tsv: Mapped[Any] = mapped_column(
        TSVECTOR, Computed("to_tsvector('simple', text)", persisted=True)
    )

    entity: Mapped[Entity] = relationship(back_populates="chunks")

    __table_args__ = (
        Index(
            "ix_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index(
            "ix_chunks_text_trgm",
            "text",
            postgresql_using="gin",
            postgresql_ops={"text": "gin_trgm_ops"},
        ),
        Index("ix_chunks_tsv", "tsv", postgresql_using="gin"),
        Index("ix_chunks_entity_id", "entity_id"),
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audience: Mapped[str] = mapped_column(String, default="general")
    created_at: Mapped[datetime] = mapped_column(default=_now, server_default=func.now())


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    # Set on an assistant "clarify" turn: [{"entity_id": ..., "label": ...}, ...] plus the intent.
    pending_clarify: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    trace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now, server_default=func.now())


class TraceRow(Base):
    __tablename__ = "traces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    question: Mapped[str] = mapped_column(Text)
    capability: Mapped[str] = mapped_column(String, index=True)
    intent: Mapped[str] = mapped_column(String, index=True)
    channel: Mapped[str] = mapped_column(String, index=True)
    language: Mapped[str] = mapped_column(String(2))
    latency_ms: Mapped[int] = mapped_column(Integer)
    data: Mapped[dict[str, Any]]
    created_at: Mapped[datetime] = mapped_column(
        default=_now, server_default=func.now(), index=True
    )


class KnowledgeGap(Base):
    __tablename__ = "knowledge_gaps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(2))
    reason: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBED_DIM))
    count: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(
        Enum("open", "resolved", "ignored", name="gap_status"), default="open", index=True
    )
    resolution_faq_id: Mapped[str | None] = mapped_column(String, nullable=True)
    first_seen: Mapped[datetime] = mapped_column(default=_now, server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(default=_now, server_default=func.now())


class ExternalCache(Base):
    __tablename__ = "external_cache"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[str] = mapped_column(String)
    payload: Mapped[dict[str, Any]]
    fetched_at: Mapped[datetime] = mapped_column(default=_now)
    ttl_seconds: Mapped[int] = mapped_column(Integer)


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(default=_now, server_default=func.now())
    prompt_version: Mapped[str] = mapped_column(String)
    model: Mapped[str] = mapped_column(String)
    subset: Mapped[str | None] = mapped_column(String, nullable=True)
    total: Mapped[int] = mapped_column(Integer)
    passed: Mapped[int] = mapped_column(Integer)
    summary: Mapped[dict[str, Any]]

    results: Mapped[list["EvalResult"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", passive_deletes=True
    )


class EvalResult(Base):
    __tablename__ = "eval_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("eval_runs.id", ondelete="CASCADE"), index=True
    )
    case_id: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)
    passed: Mapped[bool]
    details: Mapped[dict[str, Any]]

    run: Mapped[EvalRun] = relationship(back_populates="results")
