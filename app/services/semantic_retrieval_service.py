from typing import List
from sentence_transformers import SentenceTransformer
from app.models import Chunk
import numpy as np

class SemanticRetrievalService:
    """Semantic retrieval using sentence embeddings."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
    
    def retrieve(self, question: str, chunks: List[Chunk], top_k: int = 3) -> List[Chunk]:
        """
        Retrieve chunks using semantic similarity.
        
        Args:
            question: User question
            chunks: Available chunks
            top_k: Number of results to return
        
        Returns:
            Top-k chunks ranked by cosine similarity
        """
        if not chunks:
            return []
        
        # Embed question and chunks
        question_embedding = self.model.encode(question)
        chunk_embeddings = self.model.encode([c.text_preview for c in chunks])
        
        # Cosine similarity
        scores = np.dot(chunk_embeddings, question_embedding) / (
            np.linalg.norm(chunk_embeddings, axis=1) * np.linalg.norm(question_embedding)
        )
        
        # Rank
        ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)[:top_k]
        
        result = []
        for chunk, score in ranked:
            chunk.score = float(score)
            result.append(chunk)
        
        return result