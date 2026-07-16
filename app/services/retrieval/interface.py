from abc import ABC, abstractmethod
from typing import List
from app.models import Chunk

class Retriever(ABC):
    """Abstract base class for all retrieval strategies."""
    
    @abstractmethod
    def retrieve(self, question: str, chunks: List[Chunk], top_k: int = 3, min_score: float = 0.0) -> List[Chunk]:
        """Retrieve top-k chunks with optional threshold."""
        pass