from pydantic import BaseModel
from typing import List, Optional

class DocumentCreate(BaseModel):
    name: str
    text: str

class DocumentResponse(BaseModel):
    document_id: str
    name: str
    chunk_count: int

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

class AnswerResponse(BaseModel):
    question: str
    answer: Optional[str] = None
    citations: List[str] = []
    retrieved_chunks: List[AnswerChunkRef] = []
    message: Optional[str] = None