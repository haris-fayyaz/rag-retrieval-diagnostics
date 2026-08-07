from pydantic import BaseModel, field_validator
from typing import List, Optional, Literal
from datetime import datetime

from app.core.config import settings
 
 
def _validate_question(value: str) -> str:
    """Shared by AskRequest/AnswerRequest - kept as a plain function
    (not a shared base class) since the two models stay uncoupled on
    purpose, see AnswerRequest's docstring below."""
    if not value.strip():
        raise ValueError("question cannot be empty")
    if len(value) > settings.max_question_characters:
        raise ValueError(f"question exceeds {settings.max_question_characters} characters")
    return value
 
 
def _validate_top_k(value: int) -> int:
    if not 1 <= value <= settings.max_top_k:
        raise ValueError(f"top_k must be between 1 and {settings.max_top_k}")
    return value
 
 
def _validate_min_score(value: float) -> float:
    if not 0.0 <= value <= 1.0:
        raise ValueError("min_score must be between 0.0 and 1.0")
    return value
 
 
def _validate_document_ids(value: Optional[List[str]]) -> Optional[List[str]]:
    if value is not None and len(value) != len(set(value)):
        raise ValueError("document_ids contains duplicates")
    return value

class DocumentCreate(BaseModel):
    name: str
    text: str
    
    @field_validator("name")
    @classmethod
    def check_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name cannot be empty")
        if len(value) > settings.max_document_name_length:
            raise ValueError(f"name exceeds {settings.max_document_name_length} characters")
        return value
 
    @field_validator("text")
    @classmethod
    def check_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text cannot be empty")
        if len(value) > settings.max_document_characters:
            raise ValueError(f"text exceeds {settings.max_document_characters} characters")
        return value

class DocumentResponse(BaseModel):
    document_id: str
    name: str
    chunk_count: int

class ReindexResponse(BaseModel):
    document_id: str
    previous_chunk_count: int
    new_chunk_count: int

class AnswerRunResponse(BaseModel):
    """One stored audit record for a past /answer call. Mirrors
    AnswerRunORM, but with retrieved_chunk_ids/citations deserialized
    back into real lists instead of the JSON-text they're stored as."""
    request_id: str
    question: str
    answer: Optional[str] = None
    status: str  # "success" | "no_context" | "provider_error"
    retrieval_mode: str
    top_k: int
    min_score: float
    provider: str
    model: Optional[str] = None
    pipeline_mode: str  # "custom" | "langchain"
    retrieved_chunk_ids: List[str]
    citations: List[str]
    retrieval_ms: Optional[float] = None
    generation_ms: Optional[float] = None
    total_ms: Optional[float] = None
    created_at: datetime

class Chunk(BaseModel):
    document_id: str
    document_name: str
    chunk_id: str
    score: float
    text_preview: str

class AskRequest(BaseModel):
    question: str
    top_k: int = 3
    document_ids: Optional[List[str]] = None
    # 0.0 let zero-overlap chunks (score == 0, e.g. "Hi") still pass through
    # as "top_k results" even though they share no vocabulary with the
    # question at all. A small positive floor filters those out by default.
    min_score: float = 0.05
    retrieval_mode: str = "tfidf"  # "tfidf" or "semantic"
    
    @field_validator("question")
    @classmethod
    def check_question(cls, value: str) -> str:
        return _validate_question(value)
 
    @field_validator("top_k")
    @classmethod
    def check_top_k(cls, value: int) -> int:
        return _validate_top_k(value)
 
    @field_validator("min_score")
    @classmethod
    def check_min_score(cls, value: float) -> float:
        return _validate_min_score(value)
 
    @field_validator("document_ids")
    @classmethod
    def check_document_ids(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        return _validate_document_ids(value)

class AskResponse(BaseModel):
    question: str
    top_k: int
    retrieved_chunks: List[Chunk]
    message: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    
class DocData(BaseModel):
    name: str
    text: str
    chunks: List[Chunk]
    
class AnswerRequest(BaseModel):
    """Same shape as AskRequest - /answer runs the identical retrieval
    step, then adds generation on top. Kept as a separate model (not
    reused) so the two endpoints can diverge later without coupling."""
    question: str
    top_k: int = 3
    document_ids: Optional[List[str]] = None
    # 0.0 let zero-overlap chunks (score == 0, e.g. "Hi") still pass through
    # as "top_k results" even though they share no vocabulary with the
    # question at all. A small positive floor filters those out by default.
    min_score: float = 0.05
    retrieval_mode: str = "tfidf"  # "tfidf", "semantic", or "hybrid"
    # "custom" (default, existing hand-rolled prompt/provider path) or
    # "langchain" (optional LCEL pipeline - see app/chains/). A Literal
    # (not a plain str + manual check like retrieval_mode below) since
    # this is a fixed two-value switch, not a registry lookup - pydantic
    # rejects anything else with a 422 before the request body even
    # reaches generate_answer, no custom validator needed.
    pipeline_mode: Literal["custom", "langchain"] = "custom"

    @field_validator("question")
    @classmethod
    def check_question(cls, value: str) -> str:
        return _validate_question(value)
 
    @field_validator("top_k")
    @classmethod
    def check_top_k(cls, value: int) -> int:
        return _validate_top_k(value)
 
    @field_validator("min_score")
    @classmethod
    def check_min_score(cls, value: float) -> float:
        return _validate_min_score(value)
 
    @field_validator("document_ids")
    @classmethod
    def check_document_ids(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        return _validate_document_ids(value)

class AnswerChunkRef(BaseModel):
    """Slim source reference for /answer responses - enough to
    identify, cite, and preview a chunk without echoing the full text
    back (the answer already contains the grounded content in full).

    text_snippet, not text_preview: Chunk.text_preview elsewhere in
    this file holds the FULL chunk text despite its name (retrieval/
    prompt building need the whole thing). This field is genuinely
    truncated, a different name avoids the same word meaning two
    different things in this same module.
    """
    chunk_id: str
    document_id: str
    document_name: str
    score: float
    text_snippet: str

class AnswerMetadata(BaseModel):
    """
    Execution metadata for /answer - lets a slow or failing request be
    diagnosed from the response/logs alone, without stepping through
    code: was retrieval slow, or generation? How many chunks matched?
    Which retrieval mode and provider actually ran?
    """
    retrieval_ms: float
    generation_ms: Optional[float] = None  # None when the LLM was never called (no-context)
    total_ms: float
    retrieved_chunk_count: int
    retrieval_mode: str
    provider: str

class AnswerResponse(BaseModel):
    request_id: str
    question: str
    answer: Optional[str] = None
    citations: List[str] = []
    retrieved_chunks: List[AnswerChunkRef] = []
    message: Optional[str] = None
    metadata: Optional[AnswerMetadata] = None
    
class TokenRequest(BaseModel):
    """Credentials for POST /auth/token. Single hardcoded user, no signup."""
    username: str
    password: str
 
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds, mirrors JWT_EXPIRE_MINUTES
    
class AgentQueryRequest(BaseModel):
    """
    Request to POST /agent/query, the bounded LangGraph document
    assistant. Same input fields as AgentState (see app/agent/state.py).

    No retrieval_mode field: unlike /ask and /answer, the agent's
    retriever is built once at graph-construction time (see
    app/agent/document_assistant_graph.py), not chosen per request -
    including a retrieval_mode field here would silently be ignored.
    """
    query: str
    document_ids: Optional[List[str]] = None
    top_k: int = 3
    min_score: float = 0.05

    @field_validator("query")
    @classmethod
    def check_query(cls, value: str) -> str:
        return _validate_question(value)

    @field_validator("top_k")
    @classmethod
    def check_top_k(cls, value: int) -> int:
        return _validate_top_k(value)

    @field_validator("min_score")
    @classmethod
    def check_min_score(cls, value: float) -> float:
        return _validate_min_score(value)

    @field_validator("document_ids")
    @classmethod
    def check_document_ids(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        return _validate_document_ids(value)

class AgentCitation(BaseModel):
    """
    One citation from /agent/query. Unlike AnswerResponse.citations
    (plain chunk_id strings), this carries document_id/document_name
    alongside the chunk_id, so a caller can render a source without a
    second lookup back to the document store.
    """
    chunk_id: str
    document_id: str
    document_name: str

class AgentQueryResponse(BaseModel):
    """
    Response from POST /agent/query.

    answer is always a plain string, never None - generate_response_node
    in the graph always produces a human-readable message, including
    for refusals ("I can only search...") and tool errors ("Something
    went wrong: ...")Unlike AnswerResponse where answer can be None.
    """
    request_id: str
    answer: str
    # None only when the router refused the request (status="refused") -
    # otherwise one of: search_documents, list_documents, get_answer_run
    selected_tool: Optional[str] = None
    citations: List[AgentCitation] = []
    step_count: int
    status: str  # "success" | "no_context" | "refused" | "tool_error"
    # Raw error detail, already folded into `answer` as human-readable
    # text - present here too for callers that want to branch on it
    # programmatically instead of parsing `answer`.
    error: Optional[str] = None