"""
Read-only tools for the document assistant graph.

Each tool wraps an existing service (retriever or repository) and
returns plain, JSON-serializable dicts - never ORM objects or Pydantic
models directly - so results drop cleanly into AgentState.

Tools take explicit parameters, never the AgentState dict itself. This
keeps them independently unit-testable and reusable outside the graph.
"""

from typing import Any, Dict, List, Optional

from app.core.logging import get_logger, log_event
from app.database.repositories.interface import DocumentRepository
from app.services.retrieval.interface import Retriever
from app.services.version_filter import apply_version_filter

logger = get_logger()


class ToolError(Exception):
    """Raised on genuine tool failure. Caught by the graph's execute
    node and converted into a controlled AgentState error - callers
    never see a raw traceback."""


def search_documents(
    query: str,
    document_ids: Optional[List[str]],
    top_k: int,
    min_score: float,
    repo: DocumentRepository,
    retriever: Retriever,
) -> Dict[str, Any]:
    """
    Retrieve the top_k most relevant chunks for `query`.

    Zero matching chunks is a valid result, not an error - the caller
    decides how to present "nothing found" to the user.

    Also returns an "ambiguous_policy_version" key instead of scoring
    anything (Task 25) if document_ids was omitted and two or more
    active documents share a policy with no way to resolve which is
    current - same shared rule /ask and /answer use. See
    app/services/version_filter.py.
    """
    try:
        candidate_chunks = repo.get_chunks(document_ids)
    except Exception as exc:
        log_event(logger, "tool_search_documents_failed", stage="get_chunks", error=str(exc))
        raise ToolError(f"Could not load chunks: {exc}") from exc

    if not candidate_chunks:
        return {"chunk_count": 0, "chunks": []}

    # Version-aware filtering (Task 25) - same shared rule /ask and
    # /answer use, applied here so the agent never guesses either.
    filter_result = apply_version_filter(candidate_chunks, document_ids, repo)
    if filter_result.ambiguity is not None:
        log_event(logger, "tool_search_documents_ambiguous")
        return {
            "chunk_count": 0,
            "chunks": [],
            "ambiguous_policy_version": {
                "message": filter_result.ambiguity.message,
                "documents": [
                    {"document_id": d.document_id, "version": d.version}
                    for d in filter_result.ambiguity.documents
                ],
            },
        }
    candidate_chunks = filter_result.chunks

    if not candidate_chunks:
        return {"chunk_count": 0, "chunks": []}

    try:
        retrieved = retriever.retrieve(query, candidate_chunks, top_k, min_score)
    except Exception as exc:
        log_event(logger, "tool_search_documents_failed", stage="retrieve", error=str(exc))
        raise ToolError(f"Retrieval failed: {exc}") from exc

    chunks = [
        {
            "chunk_id": c.chunk_id,
            "document_id": c.document_id,
            "document_name": c.document_name,
            "score": c.score,
            "text_preview": c.text_preview,
        }
        for c in retrieved
    ]
    log_event(logger, "tool_search_documents_succeeded", chunk_count=len(chunks))
    return {"chunk_count": len(chunks), "chunks": chunks}


def list_documents(repo: DocumentRepository) -> Dict[str, Any]:
    """List all stored documents with their chunk counts."""
    try:
        documents = repo.list_documents()
    except Exception as exc:
        log_event(logger, "tool_list_documents_failed", error=str(exc))
        raise ToolError(f"Could not list documents: {exc}") from exc

    payload = [
        {"document_id": d.document_id, "name": d.name, "chunk_count": d.chunk_count}
        for d in documents
    ]
    log_event(logger, "tool_list_documents_succeeded", document_count=len(payload))
    return {"document_count": len(payload), "documents": payload}

def _citations_from_chunk_ids(chunk_ids: List[str], repo: DocumentRepository) -> List[Dict[str, str]]:
    """
    Resolve raw chunk_ids (as stored on a past AnswerRun) into full
    citation dicts with document_id/document_name attached.

    Only get_answer_run needs this: unlike search_documents, a stored
    AnswerRun.citations list is just chunk_id strings, no document
    metadata travels with it. If a document has since been deleted,
    its chunk_ids are silently skipped - a historical audit lookup
    should not fail just because the source document is gone.
    """
    if not chunk_ids:
        return []
    chunk_by_id = {c.chunk_id: c for c in repo.get_chunks()}
    return [
        {
            "chunk_id": cid,
            "document_id": chunk_by_id[cid].document_id,
            "document_name": chunk_by_id[cid].document_name,
        }
        for cid in chunk_ids
        if cid in chunk_by_id
    ]
    
def get_answer_run(request_id: str, repo: DocumentRepository) -> Dict[str, Any]:
    """
    Fetch the stored audit record for a previous /answer call.

    request_id is always an explicit parameter - never inferred from
    free-text query. The caller (router) is responsible for deciding
    when a request actually contains a real request_id.
    """
    try:
        run = repo.get_answer_run(request_id)
    except Exception as exc:
        log_event(logger, "tool_get_answer_run_failed", request_id=request_id, error=str(exc))
        raise ToolError(f"Could not look up audit record: {exc}") from exc

    if run is None:
        raise ToolError(f"No audit record found for request_id: {request_id}")

    log_event(logger, "tool_get_answer_run_succeeded", request_id=request_id, status=run.status)
    return {
        "request_id": run.request_id,
        "question": run.question,
        "answer": run.answer,
        "status": run.status,
        "citations": run.citations,
        "retrieved_chunk_ids": run.retrieved_chunk_ids,
        "retrieval_ms": run.retrieval_ms,
        "generation_ms": run.generation_ms,
        "total_ms": run.total_ms,
        "created_at": run.created_at.isoformat(),
    }