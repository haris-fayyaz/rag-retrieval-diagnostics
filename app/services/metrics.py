from typing import List
from app.models import Chunk

class MetricsCalculator:
    """Calculate retrieval metrics."""
    
    @staticmethod
    def top_1_accuracy(expected_docs: List[str], retrieved: List[Chunk]) -> bool:
        """Check if top-1 result matches expected."""
        if not retrieved or not expected_docs:
            return len(expected_docs) == 0 and not retrieved
        top_doc = retrieved[0].document_id
        return top_doc in expected_docs
    
    @staticmethod
    def recall_at_k(expected_docs: List[str], retrieved: List[Chunk], k: int = 3) -> float:
        """Calculate Recall@K."""
        if not expected_docs:
            return 1.0
        
        top_k_chunks = retrieved[:k]
        retrieved_docs = {chunk.document_id for chunk in top_k_chunks}
        expected_set = set(expected_docs)
        
        if not expected_set:
            return 1.0
        
        recall = len(retrieved_docs & expected_set) / len(expected_set)
        return recall
    
    @staticmethod
    def no_answer_accuracy(expected_docs: List[str], retrieved: List[Chunk]) -> bool:
        """Check if no-answer is correct."""
        return len(expected_docs) == 0 and len(retrieved) == 0


class ScoreDistribution:
    """Track score statistics for threshold analysis."""
    
    def __init__(self):
        self.answerable_scores = []
        self.unanswerable_scores = []
    
    def add_answerable(self, score: float):
        """Add score for answerable question."""
        self.answerable_scores.append(score)
    
    def add_unanswerable(self, score: float):
        """Add score for unanswerable question."""
        self.unanswerable_scores.append(score)
    
    def avg_answerable(self) -> float:
        """Average score for answerable questions."""
        return sum(self.answerable_scores) / len(self.answerable_scores) if self.answerable_scores else 0.0
    
    def avg_unanswerable(self) -> float:
        """Average score for unanswerable questions."""
        return sum(self.unanswerable_scores) / len(self.unanswerable_scores) if self.unanswerable_scores else 0.0
    
    def max_answerable(self) -> float:
        """Max score for answerable questions."""
        return max(self.answerable_scores) if self.answerable_scores else 0.0
    
    def max_unanswerable(self) -> float:
        """Max score for unanswerable questions."""
        return max(self.unanswerable_scores) if self.unanswerable_scores else 0.0