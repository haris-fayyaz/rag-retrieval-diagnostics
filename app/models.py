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