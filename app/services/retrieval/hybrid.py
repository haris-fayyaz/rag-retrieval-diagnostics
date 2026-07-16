from typing import List, Dict
from app.models import Chunk
from app.services.retrieval.interface import Retriever
from app.services.retrieval.tfidf import TFIDFRetriever
from app.services.retrieval.semantic import SemanticRetrievalService

class HybridRetriever(Retriever):
    """Hybrid retrieval using Reciprocal Rank Fusion (RRF)."""
    
    def __init__(self, k: int = 60):
        """
        Args:
            k: RRF constant (default 60, controls rank weight)
        """
        self.k = k
        self.tfidf_retriever = TFIDFRetriever()
        self.semantic_retriever = SemanticRetrievalService()
    
    def retrieve(self, question: str, chunks: List[Chunk], top_k: int = 3, min_score: float = 0.0) -> List[Chunk]:
        """
        Hybrid retrieval combining TF-IDF and semantic using RRF.
        
        Flow:
        1. Get results from TF-IDF (with threshold)
        2. Get results from semantic (with threshold)
        3. Combine using RRF score
        4. Return top-k
        
        Args:
            question: User question
            chunks: Available chunks
            top_k: Number of results to return
            min_score: Minimum score threshold
        
        Returns:
            Top-k chunks ranked by RRF score
        """
        
        # Get results from both retrievers (retrieve more to account for filtering)
        tfidf_results = self.tfidf_retriever.retrieve(question, chunks, top_k=top_k*2, min_score=0.10)
        semantic_results = self.semantic_retriever.retrieve(question, chunks, top_k=top_k*2, min_score=0.15)
        
        # If both return nothing, return empty
        if not tfidf_results and not semantic_results:
            return []
        
        # Combine results using RRF
        rrf_scores: Dict[str, float] = {}
        
        # Score TF-IDF results: RRF formula = 1 / (k + rank)
        for rank, chunk in enumerate(tfidf_results, 1):
            chunk_id = chunk.chunk_id
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1 / (self.k + rank)
        
        # Score semantic results with same formula
        for rank, chunk in enumerate(semantic_results, 1):
            chunk_id = chunk.chunk_id
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1 / (self.k + rank)
        
        # Merge chunks (keep first occurrence from either retriever)
        chunk_map = {}
        for chunk in tfidf_results + semantic_results:
            if chunk.chunk_id not in chunk_map:
                chunk_map[chunk.chunk_id] = chunk
        
        # Sort by RRF score and return top-k
        ranked = sorted(
            [(chunk_map[cid], score) for cid, score in rrf_scores.items()],
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        
        result = []
        for chunk, score in ranked:
            chunk.score = float(score)  # Update score to RRF score
            result.append(chunk)
        
        return result