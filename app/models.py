from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class DocumentCreate(BaseModel):
    name: str
    text: str

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
    min_score: float = 0.0
    retrieval_mode: str = "tfidf"  # "tfidf" or "semantic"

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
    min_score: float = 0.0
    retrieval_mode: str = "tfidf"  # "tfidf", "semantic", or "hybrid"

class AnswerChunkRef(BaseModel):
    """Slim source reference for /answer responses - just enough to
    identify and cite a chunk. Deliberately excludes text_preview:
    the answer already contains the grounded text, so echoing full
    chunk content back would be redundant."""
    chunk_id: str
    document_id: str
    document_name: str
    score: float

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