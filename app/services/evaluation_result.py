from dataclasses import dataclass

@dataclass
class EvaluationResult:
    """Structured evaluation results."""
    
    mode: str
    threshold: float
    top_k: int
    
    # Overall metrics
    total_questions: int
    passed: int
    failed: int
    accuracy: float
    
    # Detailed metrics
    top_1_accuracy: float
    recall_at_k: float
    no_answer_accuracy: float
    
    # Score statistics
    avg_answerable_score: float
    avg_unanswerable_score: float
    max_answerable_score: float
    max_unanswerable_score: float
    
    def print_summary(self):
        """Print results in formatted table."""
        print(f"\n{'='*80}")
        print(f"Mode: {self.mode} | Threshold: {self.threshold} | Top-K: {self.top_k}")
        print(f"{'='*80}")
        print(f"Accuracy: {self.accuracy:.1f}% ({self.passed}/{self.total_questions})")
        print(f"\nDetailed Metrics:")
        print(f"  Top-1 Accuracy: {self.top_1_accuracy:.1f}%")
        print(f"  Recall@{self.top_k}: {self.recall_at_k:.1f}%")
        print(f"  No-answer Accuracy: {self.no_answer_accuracy:.1f}%")
        print(f"\nScore Distribution:")
        print(f"  Avg Answerable Score: {self.avg_answerable_score:.3f}")
        print(f"  Avg Unanswerable Score: {self.avg_unanswerable_score:.3f}")
        print(f"  Max Answerable Score: {self.max_answerable_score:.3f}")
        print(f"  Max Unanswerable Score: {self.max_unanswerable_score:.3f}")
        print(f"{'='*80}\n")