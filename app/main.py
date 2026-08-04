from app.core.config import settings
from app.core.logging import configure_logging
from app.llm.ollama_provider import OllamaLLMProvider
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.language_models.chat_models import BaseChatModel
import jwt
import uuid
from app.models import (
    DocumentCreate, DocumentResponse, AskRequest, AskResponse, HealthResponse,
    AnswerRequest, AnswerResponse, ReindexResponse, AnswerRunResponse,
    TokenRequest, TokenResponse, AgentQueryRequest, AgentQueryResponse,
)
from app.core.security import verify_password, create_access_token, decode_access_token
from app.core.rate_limit import rate_limit
from app.database.repositories.interface import DocumentRepository
from app.database.repositories.sqlite_repository import SQLiteDocumentRepository
from app.llm.fake_provider import FakeLLMProvider
from app.llm.exceptions import LLMProviderError
from app.llm.provider import LLMProvider
from app.chains.langchain_answer_chain import get_chat_model
from app.agent.document_assistant_graph import build_document_assistant_graph
from app.agent.router import build_router
from app.services.answer_service import generate_answer
from app.services.chunking_service import chunk_text
from app.services.retrieval import get_retriever
from app.core.logging import get_logger, log_event
import time

configure_logging()  # must run before anything logs - see app/core/logging.py
app = FastAPI(title="RAG Retrieval Diagnostics")

# allow_credentials=False on purpose: auth is a Bearer token the caller
# sets explicitly, not a cookie, so CORS "credentials" mode (which only
# governs cookies/browser-managed auth) isn't needed. Side effect: the
# wildcard-origin-plus-credentials misconfiguration the task warns
# about can't happen here, since credentials are always off.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


# Same singleton-at-import-time pattern as _llm_provider above, switched
# on the same LLM_PROVIDER setting - get_chat_model() itself decides
# FakeListChatModel vs ChatOllama (see app/chains/langchain_answer_chain.py).
# Built once regardless of whether any request actually uses
# pipeline_mode="langchain" - same cost as the custom provider, no lazy
# construction per request.
_langchain_model = get_chat_model()

def get_langchain_model() -> BaseChatModel:
    """FastAPI dependency - overridden in tests with a controllable fake."""
    return _langchain_model


logger = get_logger()

# Agent graph, built once at import time - never rebuilt per request
# (see app/agent/document_assistant_graph.py's own docstring on this).
# Fixed to "tfidf" specifically: unlike /ask and /answer, the agent
# has no per-request retrieval_mode field (see AgentQueryRequest), so
# one retriever has to be picked once. tfidf matches this app's
# overall default and needs no extra runtime dependency (no torch/
# sentence-transformers) just to start the app.
_agent_retriever = get_retriever("tfidf")
_agent_router = build_router(_llm_provider, use_llm=(settings.llm_provider == "ollama"))
_agent_graph = build_document_assistant_graph(_repository, _agent_retriever, _agent_router)

def get_agent_graph():
    """FastAPI dependency - overridden in tests with a graph built
    against mocked repo/retriever/router."""
    return _agent_graph

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

@app.post(
    "/auth/token",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit(settings.rate_limit_auth_token))],
)
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

@app.post(
    "/documents", 
    response_model=DocumentResponse, 
    dependencies=[Depends(rate_limit(settings.rate_limit_auth_token, get_current_user))],
    )
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


@app.get(
    "/documents", 
    response_model=list[DocumentResponse],
    dependencies=[Depends(rate_limit(settings.rate_limit_auth_token, get_current_user))],
)
def list_documents(repo: DocumentRepository = Depends(get_repository), user: str = Depends(get_current_user)):
    """List all stored documents."""
    return repo.list_documents()


@app.post(
    "/documents/{document_id}/reindex",
    response_model=ReindexResponse,
    dependencies=[Depends(rate_limit(settings.rate_limit_auth_token, get_current_user))],
)
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


@app.post(
    "/ask", 
    response_model=AskResponse,
    dependencies=[Depends(rate_limit(settings.rate_limit_auth_token, get_current_user))],
)
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


@app.post(
    "/answer", 
    response_model=AnswerResponse,
    dependencies=[Depends(rate_limit(settings.rate_limit_auth_token, get_current_user))],
)
def answer(
    request: AnswerRequest,
    repo: DocumentRepository = Depends(get_repository),
    provider: LLMProvider = Depends(get_llm_provider),
    langchain_model: BaseChatModel = Depends(get_langchain_model),
    user: str = Depends(get_current_user),
):
    """
    User-facing question-answering endpoint.

    Unlike /ask (retrieval debug - returns raw scored chunks), this
    retrieves chunks, grounds a prompt in them, and returns a natural-
    language answer with citations. All logic lives in answer_service;
    this endpoint only maps its exceptions to HTTP responses.

    Both langchain_model and provider are always injected regardless of
    request.pipeline_mode - each is a cheap singleton lookup (see
    get_llm_provider/get_langchain_model above), not built per request,
    so a "custom" request pays nothing extra for langchain_model being
    present and unused.

    A request_id is generated here (not inside answer_service) so it's
    available even when generate_answer raises before building a
    response - every outcome (success, 400, 502) carries the same ID.
    """
    request_id = str(uuid.uuid4())
    try:
        return generate_answer(request, repo, provider, request_id, langchain_model=langchain_model)
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


@app.get(
    "/answer-runs/{request_id}", 
    response_model=AnswerRunResponse,
    dependencies=[Depends(rate_limit(settings.rate_limit_auth_token, get_current_user))],
)
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



@app.post(
    "/agent/query",
    response_model=AgentQueryResponse,
    dependencies=[Depends(rate_limit(settings.rate_limit_answer, get_current_user))],
)
def agent_query(request: AgentQueryRequest, graph=Depends(get_agent_graph), user: str = Depends(get_current_user)):
    """
    Bounded LangGraph document assistant - routes a query to one of
    three read-only tools (search_documents, list_documents,
    get_answer_run), executes it, and returns a grounded answer.

    Unlike /answer, there's no try/except here mapping exception types
    to status codes - the graph itself already converts every failure
    (an unroutable request, a tool error) into a controlled AgentState
    result before this function ever sees it. See
    app/agent/document_assistant_graph.py's generate_response_node.
    """
    request_id = str(uuid.uuid4())
    initial_state = {
        "request_id": request_id,
        "query": request.query,
        "document_ids": request.document_ids,
        "top_k": request.top_k,
        "min_score": request.min_score,
        "selected_tool": None,
        "tool_result": None,
        "answer": None,
        "citations": [],
        "status": "success",
        "step_count": 0,
        "error": None,
    }

    start = time.perf_counter()
    final_state = graph.invoke(initial_state)
    duration_ms = (time.perf_counter() - start) * 1000

    # Observability per the task spec: request ID, selected tool, step
    # count, duration, final status - never the query text or answer
    # content itself (see log_event's own docstring on what's safe to
    # pass).
    log_event(
        logger, "agent_query_completed",
        request_id=request_id, selected_tool=final_state["selected_tool"],
        step_count=final_state["step_count"], status=final_state["status"],
        duration_ms=duration_ms,
    )

    return AgentQueryResponse(
        request_id=request_id,
        answer=final_state["answer"],
        selected_tool=final_state["selected_tool"],
        citations=final_state["citations"],
        step_count=final_state["step_count"],
        status=final_state["status"],
        error=final_state["error"],
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)