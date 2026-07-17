from typing import List, Optional, Protocol

from app.models import Chunk, DocumentResponse


class DocumentRepository(Protocol):
    """
    Boundary between the API/retrieval layer and storage.

    The API and retrieval services depend only on this interface -
    never on SQL, SQLAlchemy sessions, or ORM classes directly.
    Any implementation (SQLite, in-memory, Postgres, ...) must satisfy it.
    """

    def add_document(self, name: str, text: str) -> DocumentResponse:
        """Create a document record (no chunks yet). Raises ValueError if text is empty."""
        ...

    def save_chunks(self, document_id: str, chunks: List[Chunk]) -> None:
        """Persist chunks for an existing document. Raises ValueError if document_id is unknown."""
        ...

    def get_document(self, document_id: str) -> Optional[dict]:
        """Return {'document_id', 'name', 'chunks'} for a document, or None if it doesn't exist."""
        ...

    def list_documents(self) -> List[DocumentResponse]:
        """List all stored documents with their chunk counts."""
        ...

    def get_chunks(self, document_ids: Optional[List[str]] = None) -> List[Chunk]:
        """Return chunks for the given document_ids, or all chunks if document_ids is None."""
        ...
