from typing import List, Optional, Protocol

from app.models import Chunk, DocumentResponse, ReindexResponse, AnswerRunResponse, SupersedeResponse


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

    def get_document_versions(self, document_ids: List[str]) -> List[DocumentResponse]:
        """
        Return version metadata (policy_name, version, effective_date,
        status) for the given document_ids, one DocumentResponse per
        existing document - unknown IDs are silently skipped, not errors
        (mirrors get_chunks' 'unknown ID matches nothing' behavior).

        Used by the version-aware filtering service (Task 25) to look up
        the status of documents represented in a candidate chunk set,
        without needing get_chunks itself to know anything about
        versioning - retrieval and version metadata stay decoupled.
        """
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

    def supersede_document(self, document_id: str, superseded_by: str) -> SupersedeResponse:
        """
        Mark document_id as 'superseded' and superseded_by as 'active',
        in one transaction (Task 25). Does not delete either document or
        their chunks - both remain queryable, including document_id by
        explicit historical lookup.

        Does not persist which document superseded which beyond the
        status flip itself - out of scope for this task, see
        docs/version-aware-retrieval.md for the tradeoff.

        Raises ValueError (mapped to a 4xx by the caller) if either ID
        doesn't exist, or if document_id == superseded_by.
        """
        ...
        
    def save_answer_run(
        self,
        request_id: str,
        question: str,
        answer: Optional[str],
        status: str,
        retrieval_mode: str,
        pipeline_mode: str,
        top_k: int,
        min_score: float,
        provider: str,
        model: Optional[str],
        retrieved_chunk_ids: List[str],
        citations: List[str],
        retrieval_ms: Optional[float],
        generation_ms: Optional[float],
        total_ms: Optional[float],
    ) -> None:
        """Persist one audit record for a completed /answer call (any
        outcome: success, no_context, or provider_error)."""
        ...

    def get_answer_run(self, request_id: str) -> Optional[AnswerRunResponse]:
        """Return the stored audit record for request_id, or None if no
        such record exists."""
        ...
        
    