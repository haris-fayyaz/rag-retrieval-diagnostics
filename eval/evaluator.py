from app.services.document_store import DocumentStore
from app.services.chunking_service import chunk_text
from app.services.retrieval import get_retriever
from app.services.metrics import MetricsCalculator, ScoreDistribution
from app.services.evaluation_result import EvaluationResult


class RetrieverEvaluator:
    """Evaluation engine for retrieval strategies."""
    
    def __init__(self, min_score: float = 0.0, mode: str = "tfidf", top_k: int = 3):
        self.min_score = min_score
        self.mode = mode
        self.top_k = top_k
        self.retriever = get_retriever(mode)
        self.metrics = MetricsCalculator()
        self.scores = ScoreDistribution()
    
    def evaluate(self, questions_data: dict, documents_data: dict) -> EvaluationResult:
        """Run evaluation and return structured result."""
        
        # Initialize document store
        doc_store = DocumentStore()
        doc_id_map = {}
        
        # Load documents
        for doc in documents_data["documents"]:
            response = doc_store.add_document(doc["name"], doc["text"])
            doc_id_map[doc["id"]] = response.document_id
            chunks = chunk_text(doc["text"], response.document_id, doc["name"])
            doc_store.update_chunks(response.document_id, chunks)
        
        # Evaluate questions
        results = []
        top1_count = 0
        recall_count = 0
        no_answer_count = 0
        
        for q in questions_data["questions"]:
            question = q["question"]
            expected_docs = q["expected_documents"]
            
            # Get all chunks
            all_chunks = []
            for doc_id, doc in doc_store.documents.items():
                all_chunks.extend(doc["chunks"])
            
            # Retrieve
            retrieved = self.retriever.retrieve(question, all_chunks, top_k=self.top_k)
            
            # Filter by threshold
            if self.mode != "hybrid":
                retrieved = [chunk for chunk in retrieved if chunk.score >= self.min_score]
            # DEBUG
            if expected_docs and not retrieved:
                print(f"Q{q['id']}: No results after threshold filtering")
            
            # Map chunk doc_ids back to original IDs for comparison
            for chunk in retrieved:
                # Convert auto-generated ID back to original
                original_id = next((k for k, v in doc_id_map.items() if v == chunk.document_id), chunk.document_id)
                chunk.document_id = original_id

            # Calculate metrics with correct document IDs
            top1_accurate = self.metrics.top_1_accuracy(expected_docs, retrieved)
            recall = self.metrics.recall_at_k(expected_docs, retrieved, k=self.top_k)
            no_answer_correct = self.metrics.no_answer_accuracy(expected_docs, retrieved)

            # Count metrics only for appropriate question type
            if expected_docs:  # Answerable
                if top1_accurate:
                    top1_count += 1
                if recall == 1.0:
                    recall_count += 1
                self.scores.add_answerable(retrieved[0].score if retrieved else 0.0)
            else:  # Unanswerable
                if no_answer_correct:
                    no_answer_count += 1
                self.scores.add_unanswerable(retrieved[0].score if retrieved else 0.0)
            
            results.append({
                "question": question,
                "expected": expected_docs,
                "retrieved": [
                    next((k for k, v in doc_id_map.items() if v == c.document_id), c.document_id)
                    for c in retrieved
                ],
                "passed": top1_accurate if expected_docs else no_answer_correct
            })
                    
        # Calculate summary metrics
        total = len(results)
        passed = sum(1 for r in results if r["passed"])
        failed = total - passed
        accuracy = (passed / total * 100) if total > 0 else 0
        
        answerable_count = sum(1 for r in results if r["expected"])
        unanswerable_count = sum(1 for r in results if not r["expected"])
        
        top_1_acc = (top1_count / answerable_count * 100) if answerable_count > 0 else 0
        recall_acc = (recall_count / answerable_count * 100) if answerable_count > 0 else 0
        no_answer_acc = (no_answer_count / unanswerable_count * 100) if unanswerable_count > 0 else 0
        
        return EvaluationResult(
            mode=self.mode,
            threshold=self.min_score,
            top_k=self.top_k,
            total_questions=total,
            passed=passed,
            failed=failed,
            accuracy=accuracy,
            top_1_accuracy=top_1_acc,
            recall_at_k=recall_acc,
            no_answer_accuracy=no_answer_acc,
            avg_answerable_score=self.scores.avg_answerable(),
            avg_unanswerable_score=self.scores.avg_unanswerable(),
            max_answerable_score=self.scores.max_answerable(),
            max_unanswerable_score=self.scores.max_unanswerable()
        )