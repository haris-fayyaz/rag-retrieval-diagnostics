from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class DocumentORM(Base):
    """A stored document (maps to the 'documents' table)."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    
    # Full original text, saved once at upload time. Needed for /reindex -
    # chunking can be re-run only if the source text still exists; chunks
    # are a lossy, overlapping derivative of it and can't be reassembled
    # back into the original. Nullable: documents created before this
    # column existed have no original_text until they're re-indexed once
    # under the new flow (there's no way to recover their original text
    # retroactively - it was never stored before this migration).
    original_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    # Version-aware policy retrieval metadata (Task 25). All nullable -
    # existing documents have none of this and must keep working as
    # unversioned documents. effective_date is stored as an ISO string
    # ("2026-01-01"), not a Date column - no NL date parsing is in scope,
    # and ISO strings sort correctly for the deterministic resolution
    # rule without needing date parsing logic.
    policy_name: Mapped[str | None] = mapped_column(String, nullable=True)
    version: Mapped[str | None] = mapped_column(String, nullable=True)
    effective_date: Mapped[str | None] = mapped_column(String, nullable=True)
    # "active" | "superseded". Nullable at the DB level for old rows,
    # but new inserts default to "active" via the Python-side default.
    status: Mapped[str | None] = mapped_column(
        String, nullable=True, default="active"
    )

    chunks: Mapped[list["ChunkORM"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="ChunkORM.chunk_index",
    )


class ChunkORM(Base):
    """A chunk of a document (maps to the 'chunks' table)."""

    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    document: Mapped["DocumentORM"] = relationship(back_populates="chunks")


class AnswerRunORM(Base):
    """
    One audit record per /answer call (maps to the 'answer_runs' table).

    Deliberately has NO foreign key to documents/chunks - an audit record
    must survive even if the underlying document is later deleted or
    re-indexed. request_id is the primary key since every lookup
    (GET /answer-runs/{request_id}) is by that ID, never by a separate
    surrogate key.

    retrieved_chunk_ids and citations are stored as JSON-encoded text
    (simple lists of chunk_id strings) rather than a separate join table -
    they're write-once, read-whole, never queried/filtered individually,
    so a normalized table would add complexity with no real benefit here.

    Does NOT store: the full prompt, API keys, or full document content -
    only IDs, the question, the final answer, and timing/status metadata.
    """

    __tablename__ = "answer_runs"

    request_id: Mapped[str] = mapped_column(String, primary_key=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    # "success" | "no_context" | "provider_error"
    status: Mapped[str] = mapped_column(String, nullable=False)
    # "custom" | "langchain" - which pipeline generated this answer.
    # Separate from `provider` ("fake"/"ollama" - which backend), so the
    # comparison script can filter/group by pipeline independent of
    # which model actually ran.
    pipeline_mode: Mapped[str] = mapped_column(String, nullable=False, default="custom")
    retrieval_mode: Mapped[str] = mapped_column(String, nullable=False)
    top_k: Mapped[int] = mapped_column(nullable=False)
    min_score: Mapped[float] = mapped_column(nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    retrieved_chunk_ids: Mapped[str] = mapped_column(Text, nullable=False)  # JSON list
    citations: Mapped[str] = mapped_column(Text, nullable=False)  # JSON list
    retrieval_ms: Mapped[float | None] = mapped_column(nullable=True)
    generation_ms: Mapped[float | None] = mapped_column(nullable=True)
    total_ms: Mapped[float | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )