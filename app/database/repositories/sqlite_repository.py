import json
from typing import Dict, List, Optional

from sqlalchemy.orm import Session, sessionmaker

from app.database.models import AnswerRunORM, ChunkORM, DocumentORM
from app.database.session import make_engine
from app.models import AnswerRunResponse, Chunk, DocumentResponse, ReindexResponse


class SQLiteDocumentRepository:
    """SQLite-backed implementation of DocumentRepository (SQLAlchemy ORM)."""

    def __init__(self, database_url: Optional[str] = None):
        self.engine = make_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

    def add_document(self, name: str, text: str) -> DocumentResponse:
        if not text.strip():
            raise ValueError("Document text cannot be empty")

        with self.SessionLocal() as session:
            document = DocumentORM(name=name)
            session.add(document)
            session.commit()
            session.refresh(document)
            return DocumentResponse(document_id=str(document.id), name=document.name, chunk_count=0)

    def save_chunks(self, document_id: str, chunks: List[Chunk]) -> None:
        with self.SessionLocal() as session:
            document = self._get_document_orm(session, document_id)
            if document is None:
                raise ValueError(f"Document '{document_id}' not found")

            for index, chunk in enumerate(chunks):
                session.add(
                    ChunkORM(document_id=document.id, chunk_index=index, text=chunk.text_preview)
                )
            session.commit()

    def create_document_with_chunks(self, name: str, text: str, chunker) -> DocumentResponse:
        if not text.strip():
            raise ValueError("Document text cannot be empty")

        with self.SessionLocal() as session:
            try:
                document = DocumentORM(name=name, original_text=text)
                session.add(document)
                # flush (not commit) assigns document.id via the DB's
                # autoincrement, without ending the transaction - so the
                # chunker below can build correct chunk_ids, and everything
                # still rolls back together if chunking fails.
                session.flush()

                chunks = chunker(text, str(document.id), name)
                for index, chunk in enumerate(chunks):
                    session.add(
                        ChunkORM(document_id=document.id, chunk_index=index, text=chunk.text_preview)
                    )

                session.commit()
                return DocumentResponse(
                    document_id=str(document.id), name=name, chunk_count=len(chunks)
                )
            except Exception:
                session.rollback()
                raise

    def get_document(self, document_id: str) -> Optional[Dict]:
        with self.SessionLocal() as session:
            document = self._get_document_orm(session, document_id)
            if document is None:
                return None
            return {
                "document_id": str(document.id),
                "name": document.name,
                "chunks": self._to_chunks(document),
            }

    def list_documents(self) -> List[DocumentResponse]:
        with self.SessionLocal() as session:
            documents = session.query(DocumentORM).all()
            return [
                DocumentResponse(
                    document_id=str(document.id),
                    name=document.name,
                    chunk_count=len(document.chunks),
                )
                for document in documents
            ]

    def get_chunks(self, document_ids: Optional[List[str]] = None) -> List[Chunk]:
        with self.SessionLocal() as session:
            query = session.query(DocumentORM)

            if document_ids is not None:
                numeric_ids = self._parse_ids(document_ids)
                if not numeric_ids:
                    return []
                query = query.filter(DocumentORM.id.in_(numeric_ids))

            chunks: List[Chunk] = []
            for document in query.all():
                chunks.extend(self._to_chunks(document))
            return chunks
        
        
    def reindex_document(self, document_id: str, chunker) -> ReindexResponse:
        with self.SessionLocal() as session:
            document = self._get_document_orm(session, document_id)
            if document is None:
                raise ValueError(f"Document '{document_id}' not found")
            if not document.original_text:
                raise ValueError(
                    f"Document '{document_id}' has no saved original text "
                    "and cannot be re-indexed - it was created before "
                    "original_text was persisted. Re-upload it instead."
                )

            previous_chunk_count = len(document.chunks)

            try:
                # Build the new chunks FIRST, before touching any existing
                # row. If the chunker raises, we exit here with nothing
                # deleted yet - existing chunks are untouched.
                new_chunks = chunker(document.original_text, str(document.id), document.name)

                # Delete old chunks and add new ones inside the same
                # uncommitted transaction. If anything below raises before
                # commit(), the rollback in `except` undoes the deletes
                # too - old chunks come back exactly as they were.
                for old_chunk in list(document.chunks):
                    session.delete(old_chunk)
                session.flush()

                for index, chunk in enumerate(new_chunks):
                    session.add(
                        ChunkORM(document_id=document.id, chunk_index=index, text=chunk.text_preview)
                    )

                session.commit()
                return ReindexResponse(
                    document_id=str(document.id),
                    previous_chunk_count=previous_chunk_count,
                    new_chunk_count=len(new_chunks),
                )
            except Exception:
                session.rollback()
                raise

    def save_answer_run(
        self,
        request_id: str,
        question: str,
        answer: Optional[str],
        status: str,
        retrieval_mode: str,
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
        with self.SessionLocal() as session:
            session.add(
                AnswerRunORM(
                    request_id=request_id,
                    question=question,
                    answer=answer,
                    status=status,
                    retrieval_mode=retrieval_mode,
                    top_k=top_k,
                    min_score=min_score,
                    provider=provider,
                    model=model,
                    retrieved_chunk_ids=json.dumps(retrieved_chunk_ids),
                    citations=json.dumps(citations),
                    retrieval_ms=retrieval_ms,
                    generation_ms=generation_ms,
                    total_ms=total_ms,
                )
            )
            session.commit()

    def get_answer_run(self, request_id: str) -> Optional[AnswerRunResponse]:
        with self.SessionLocal() as session:
            run = session.get(AnswerRunORM, request_id)
            if run is None:
                return None
            return AnswerRunResponse(
                request_id=run.request_id,
                question=run.question,
                answer=run.answer,
                status=run.status,
                retrieval_mode=run.retrieval_mode,
                top_k=run.top_k,
                min_score=run.min_score,
                provider=run.provider,
                model=run.model,
                retrieved_chunk_ids=json.loads(run.retrieved_chunk_ids),
                citations=json.loads(run.citations),
                retrieval_ms=run.retrieval_ms,
                generation_ms=run.generation_ms,
                total_ms=run.total_ms,
                created_at=run.created_at,
            )
            
            
            
    # -- internal helpers -------------------------------------------------

    @staticmethod
    def _parse_ids(document_ids: List[str]) -> List[int]:
        """Silently drop malformed IDs instead of raising - an unknown/invalid
        document_id should simply match nothing, not crash retrieval."""
        parsed = []
        for doc_id in document_ids:
            try:
                parsed.append(int(doc_id))
            except (TypeError, ValueError):
                continue
        return parsed

    @staticmethod
    def _get_document_orm(session: Session, document_id: str) -> Optional[DocumentORM]:
        try:
            numeric_id = int(document_id)
        except (TypeError, ValueError):
            return None
        return session.get(DocumentORM, numeric_id)

    @staticmethod
    def _to_chunks(document: DocumentORM) -> List[Chunk]:
        return [
            Chunk(
                document_id=str(document.id),
                document_name=document.name,
                chunk_id=f"{document.id}_chunk_{chunk.chunk_index}",
                score=0.0,
                text_preview=chunk.text,
            )
            for chunk in document.chunks
        ]
