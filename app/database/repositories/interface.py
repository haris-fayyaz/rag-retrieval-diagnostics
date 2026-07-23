from typing import List, Optional, Protocol

from app.models import Chunk, DocumentResponse, ReindexResponse


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

    def create_document_with_chunks(self, name: str, text: str, chunker) -> DocumentResponse:
        """
        Create a document AND its chunks in a single transaction.

        `chunker` is a callable (text, document_id, document_name) -> List[Chunk],
        called internally once the document's ID is known but before the
        transaction commits. If chunking or chunk insertion fails, the
        document insert rolls back too - no orphaned, chunk-less document
        is ever left behind. Raises ValueError if text is empty.
        """
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

    def reindex_document(self, document_id: str, chunker) -> ReindexResponse:
        """
        Re-chunk a document's saved original_text with the current chunker
        and replace its existing chunks, in one transaction.

        Raises ValueError if the document doesn't exist, or if it has no
        original_text saved (documents created before this field existed
        must be re-uploaded, not just re-indexed - the source text was
        never stored for them). On any failure, the existing chunks are
        left completely unchanged - nothing is deleted until the new
        chunks are ready to replace them in the same transaction.
        """
        ...
        
    