from typing import List
from sklearn.feature_extraction.text import TfidfVectorizer
from app.models import Chunk
import numpy as np

class TFIDF:
    """Retrieve relevant chunks using TF-IDF scoring."""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words="english")
    
    def retrieve(self, question: str, chunks: List[Chunk], top_k: int = 3, min_score: float = 0.0) -> List[Chunk]:
        """
        Rank chunks by relevance to question using TF-IDF.
        
        Args:
            question: User question
            chunks: List of all chunks to search
            top_k: Number of top results to return
        
        Returns:
            Top-k ranked chunks with scores
        """
        if not chunks:
            return []
        
        # Extract chunk texts
        chunk_texts = [chunk.text_preview for chunk in chunks]
        
        # Fit vectorizer and compute scores
        tfidf_matrix = self.vectorizer.fit_transform(chunk_texts + [question])
        question_vector = tfidf_matrix[-1]
        chunk_vectors = tfidf_matrix[:-1]
        
        # Cosine similarity scores
        scores = chunk_vectors.dot(question_vector.T).toarray().flatten()
        
        # Rank and return top-k
        ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)[:top_k]
        
        result = []
        for chunk, score in ranked:
            if score >= min_score:  # Filter by threshold
                chunk.score = float(score)
                result.append(chunk)
        
        return result