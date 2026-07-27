from app.core.config import settings
from app.core.logging import configure_logging
from app.llm.ollama_provider import OllamaLLMProvider
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
import uuid
from app.models import (
    DocumentCreate, DocumentResponse, AskRequest, AskResponse, HealthResponse,
    AnswerRequest, AnswerResponse, ReindexResponse, AnswerRunResponse,
    TokenRequest, TokenResponse,
)
from app.core.security import verify_password, create_access_token, decode_access_token
from app.database.repositories.interface import DocumentRepository
from app.database.repositories.sqlite_repository import SQLiteDocumentRepository
from app.llm.fake_provider import FakeLLMProvider
from app.llm.exceptions import LLMProviderError
from app.llm.provider import LLMProvider
from app.services.answer_service import generate_answer
from app.services.chunking_service import chunk_text
from app.services.retrieval import get_retriever

configure_logging()  # must run before anything logs - see app/core/logging.py
app = FastAPI(title="RAG Retrieval Diagnostics")

# Single repository instance backing the running app (points at the
# SQLite file resolved by app.db.session, or DATABASE_URL if set).
_repository = SQLiteDocumentRepository()


def get_repository() -> DocumentRepository:
    """FastAPI dependency - overridden in tests to point at a temp DB."""
    return _repository



# Provider selected via settings.llm_provider (LLM_PROVIDER env var) -
# defaults to the fake, so the app runs (and CI passes) with zero LLM
# configuration. Set LLM_PROVIDER=ollama locally (see .env.example) to
# use a real model.
def _build_llm_provider() -> LLMProvider:
    if settings.llm_provider == "ollama":
        return OllamaLLMProvider(
            model=settings.llm_model,
            base_url=settings.ollama_base_url,
            timeout=settings.llm_timeout_seconds,
        )
    return FakeLLMProvider()

_llm_provider = _build_llm_provider()

def get_llm_provider() -> LLMProvider:
    """FastAPI dependency - overridden in tests with a controllable fake."""
    return _llm_provider

_bearer_scheme = HTTPBearer(auto_error=False)
 
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme)) -> str:
    """
    FastAPI dependency - require a valid JWT, returns the username (sub).
    - auto_error=False on the scheme: a missing header reaches us as
      None instead of FastAPI/HTTPBearer's default 403, so we control
      the status code and return 401 for every failure mode.
    - Missing, malformed, expired, bad-signature: all the same 401 with
      the same message, on purpose (don't leak which check failed).
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@app.get("/")
def main_app():
    return "Hello From FastAPI"

@app.get("/health", response_model=HealthResponse)
def health():
    """Health check endpoint."""
    return {"status": "ok"}

def login(credentials: TokenRequest):
    """
    Public endpoint - issues a JWT for the single configured user.
    - Wrong username or wrong password: same 401, same message. Don't
      reveal which one was wrong (no username-enumeration signal).
    - verify_password fails closed on an unset/malformed APP_PASSWORD_HASH,
      so misconfiguration blocks login instead of allowing it.
    """
    if credentials.username != settings.app_username or not verify_password(
        credentials.password, settings.app_password_hash
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(credentials.username)
    return TokenResponse(access_token=token, expires_in=settings.jwt_expire_minutes * 60)

@app.post("/documents", response_model=DocumentResponse)
def add_document(doc: DocumentCreate, repo: DocumentRepository = Depends(get_repository), user: str = Depends(get_current_user)):
    """
    Add a new document and chunk it.
    
    Args:
        doc: Document with name and text
    
    Returns:
        Document metadata with chunk count
    """
    if not doc.text.strip():
        raise HTTPException(status_code=400, detail="Document text cannot be empty")

    # Single transaction: document row and its chunks are created together,
    # or not at all. Previously this was two separate commits (add_document,
    # then save_chunks) - if the second failed, the document would be left
    # behind with zero chunks. See tests/test_persistence.py for the
    # regression test covering this.
    return repo.create_document_with_chunks(doc.name, doc.text, chunk_text)

"""
    # Previous Implementation, Not Required
"""
"""
    # Store document
    response = repo.add_document(doc.name, doc.text)

    # Chunk document and persist the chunks
    chunks = chunk_text(doc.text, response.document_id, doc.name)
    repo.save_chunks(response.document_id, chunks)

    # Update chunk count
    response.chunk_count = len(chunks)
    return response
"""


@app.get("/documents", response_model=list[DocumentResponse])
def list_documents(repo: DocumentRepository = Depends(get_repository), user: str = Depends(get_current_user)):
    """List all stored documents."""
    return repo.list_documents()


@app.post("/documents/{document_id}/reindex", response_model=ReindexResponse)
def reindex_document(document_id: str, repo: DocumentRepository = Depends(get_repository), user: str = Depends(get_current_user)):
    """
    Re-chunk a document's saved original text using the current chunking
    configuration (CHUNK_SIZE/CHUNK_OVERLAP), replacing its existing
    chunks in one transaction. Use this after changing chunk config, or
    to apply a chunking fix to a document uploaded under an older version.

    404 if the document doesn't exist. 400 if it exists but has no saved
    original_text (uploaded before that field existed - must be
    re-uploaded, not re-indexed, since the source text was never stored).
    """
    if repo.get_document(document_id) is None:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found")

    try:
        return repo.reindex_document(document_id, chunk_text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest, repo: DocumentRepository = Depends(get_repository), user: str = Depends(get_current_user)):
    """
    Retrieve relevant chunks for a question.
    
    Args:
        request: Question, top_k, and optional document filters
    Returns:
        Top-k ranked chunks with scores
    """
    # Gather persisted chunks (or filtered by document_ids)
    all_chunks = repo.get_chunks(request.document_ids)

    if not all_chunks:
        raise HTTPException(status_code=404, detail="No chunks found")
    

    # Choose retrieval mode and retrieve with threshold
    retriever = get_retriever(request.retrieval_mode)
    retrieved = retriever.retrieve(request.question, all_chunks, request.top_k, request.min_score)

    message = None
    if not retrieved:
        message = "No relevant chunks found above confidence threshold."

    return AskResponse(
        question=request.question,
        top_k=request.top_k,
        retrieved_chunks=retrieved,
        message=message
    )


@app.post("/answer", response_model=AnswerResponse)
def answer(
    request: AnswerRequest,
    repo: DocumentRepository = Depends(get_repository),
    provider: LLMProvider = Depends(get_llm_provider),
    user: str = Depends(get_current_user),
):
    """
    User-facing question-answering endpoint.

    Unlike /ask (retrieval debug - returns raw scored chunks), this
    retrieves chunks, grounds a prompt in them, and returns a natural-
    language answer with citations. All logic lives in answer_service;
    this endpoint only maps its exceptions to HTTP responses.

    A request_id is generated here (not inside answer_service) so it's
    available even when generate_answer raises before building a
    response - every outcome (success, 400, 502) carries the same ID.
    """
    request_id = str(uuid.uuid4())
    try:
        return generate_answer(request, repo, provider, request_id)
    except ValueError as e:
        # empty question or unsupported retrieval_mode
        raise HTTPException(
            status_code=400, detail={"request_id": request_id, "error": str(e)}
        )
    except LLMProviderError as e:
        # provider outage/timeout, retries exhausted - controlled error,
        # not a raw stack trace
        raise HTTPException(
            status_code=502,
            detail={"request_id": request_id, "error": f"LLM provider failed: {e}"},
        )


@app.get("/answer-runs/{request_id}", response_model=AnswerRunResponse)
def get_answer_run(request_id: str, repo: DocumentRepository = Depends(get_repository), user: str = Depends(get_current_user)):
    """
    Fetch the stored audit record for a past /answer call - what was
    asked, what was retrieved, what was answered (or why it wasn't), and
    timing. 404 if request_id was never recorded (unknown ID, or an
    audit write that itself failed - see _record_audit's docstring).
    """
    run = repo.get_answer_run(request_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"No answer run found for request_id '{request_id}'")
    return run


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)