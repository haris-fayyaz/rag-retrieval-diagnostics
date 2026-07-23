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
