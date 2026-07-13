from abc import ABC, abstractmethod
from typing import List
from app.models import Chunk

class Retriever(ABC):
    """Abstract base class for retrieval strategies."""
    
    @abstractmethod
    def retrieve(self, question: str, chunks: List[Chunk], top_k: int) -> List[Chunk]:
        """Retrieve top-k chunks relevant to question."""
        pass