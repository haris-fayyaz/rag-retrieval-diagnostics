import json
from typing import List
from app.models import Chunk
from app.services.document_store import DocumentStore
from app.services.chunking_service import chunk_text
from app.services.retrieval import get_retriever

def load_json(filepath):
    """Load JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def calculate_recall_at_k(expected_docs: List[str], retrieved: List[Chunk], k: int = 3) -> float:
    """Calculate Recall@K: how many expected docs appear in top-k results."""
    if not expected_docs:
        return 1.0  # No expected docs = perfect recall
    
    retrieved_docs = set(c.document_id.split('_')[1] if '_' in c.document_id else c.document_id 
                         for c in retrieved[:k])
    expected_set = set(expected_docs)
    
    if not expected_set:
        return 1.0
    
    recall = len(retrieved_docs & expected_set) / len(expected_set)
    return recall

def is_top1_match(expected_docs: List[str], retrieved: List[Chunk]) -> bool:
    """Check if top-1 result matches any expected document."""
    if not retrieved or not expected_docs:
        return len(expected_docs) == 0 and not retrieved
    
    top_doc = retrieved[0].document_id.split('_')[1] if '_' in retrieved[0].document_id else retrieved[0].document_id
    return top_doc in expected_docs

def is_no_answer_correct(expected_docs: List[str], retrieved: List[Chunk]) -> bool:
    """Check if no-answer is correct (expected empty and got empty)."""
    return len(expected_docs) == 0 and len(retrieved) == 0



def evaluate_retrieval(min_score=0.0, mode="tfidf"):
    """Run retrieval evaluation on test questions."""
    
    # Load data
    docs_data = load_json("eval/sample_documents.json")
    questions_data = load_json("eval/eval_questions.json")
    
    # Initialize services
    doc_store = DocumentStore()
    
    # Select the retrival mode
    retrieval_service = get_retriever(mode)
 
    
    # Add documents to store
    print("Loading documents...")
    doc_id_map = {}  # Map from doc id to document_id in store
    for doc in docs_data["documents"]:
        response = doc_store.add_document(doc["name"], doc["text"])
        doc_id_map[doc["id"]] = response.document_id
        
        # Chunk and store
        chunks = chunk_text(doc["text"], response.document_id, doc["name"])
        doc_store.update_chunks(response.document_id, chunks)
    
    print(f"Loaded {len(doc_id_map)} documents\n")
    
    # Initialize tracking
    answerable_scores = []
    unanswerable_scores = []
    top1_count = 0
    recall_count = 0
    no_answer_count = 0
        
    # Evaluate questions
    results = []
    for q in questions_data["questions"]:
        question = q["question"]
        expected_docs = q["expected_documents"]
        
        # Get all chunks
        all_chunks = []
        for doc_id, doc in doc_store.documents.items():
            all_chunks.extend(doc["chunks"])
        
        # Retrieve
        retrieved = retrieval_service.retrieve(question, all_chunks, top_k=3)
        
        # Filter by threshold
        retrieved = [chunk for chunk in retrieved if chunk.score >= min_score]
        
        # Determine result
        if not retrieved:
            top_result = None
            passed = len(expected_docs) == 0
        else:
            top_chunk = retrieved[0]
            top_result = next(
                (k for k, v in doc_id_map.items() if v == top_chunk.document_id),
                None
            )
            passed = top_result in expected_docs if expected_docs else (not retrieved)
        
        results.append({
            "id": q["id"],
            "question": question,
            "expected": expected_docs,
            "top_result": top_result,
            "passed": passed
        })
        
    
        top1_accurate = is_top1_match(expected_docs, retrieved)
        recall_at_3 = calculate_recall_at_k(expected_docs, retrieved, k=3)
        no_answer_correct = is_no_answer_correct(expected_docs, retrieved)

        if top1_accurate:
            top1_count += 1
        if recall_at_3 == 1.0:
            recall_count += 1
        if no_answer_correct:
            no_answer_count += 1

        # Track scores
        if expected_docs:  # Answerable
            answerable_scores.append(retrieved[0].score if retrieved else 0.0)
        else:  # Unanswerable
            unanswerable_scores.append(retrieved[0].score if retrieved else 0.0)
            
    
    # Print results table
    print("-" * 100)
    print(f"{'Question':<40} {'Expected':<15} {'Top Result':<15} {'Pass':<10}")
    print("-" * 100)
    
    for r in results:
        passed_str = "✓" if r["passed"] else "✗"
        print(f"{r['question']:<40} {str(r['expected']):<15} {str(r['top_result']):<15} {passed_str:<10}")
    
    # Summary metrics
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    accuracy = (passed / total * 100) if total > 0 else 0
    
    print("-" * 100)
    print("\nSummary:")
    print(f"  Total questions: {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Accuracy: {accuracy:.1f}%")
    
    
    avg_answerable = sum(answerable_scores) / len(answerable_scores) if answerable_scores else 0
    avg_unanswerable = sum(unanswerable_scores) / len(unanswerable_scores) if unanswerable_scores else 0

    print(f"\nMetrics:")
    answerable_count = sum(1 for r in results if r["expected"])
    unanswerable_count = sum(1 for r in results if not r["expected"])
    print(f"  Top-1 Accuracy: {top1_count}/{answerable_count} = {top1_count/answerable_count*100:.1f}%")
    print(f"  Recall@3: {recall_count}/{answerable_count} = {recall_count/answerable_count*100:.1f}%")
    print(f"  No-answer Accuracy: {no_answer_count}/{unanswerable_count} = {no_answer_count/unanswerable_count*100:.1f}%")
    print(f"  Avg Answerable Score: {avg_answerable:.3f}")
    print(f"  Avg Unanswerable Score: {avg_unanswerable:.3f}")


if __name__ == "__main__":
    
    # add CLI support
    import sys
    mode = "tfidf"
    min_score = 0.0
    
    if "--mode" in sys.argv:
        mode = sys.argv[sys.argv.index("--mode") + 1]
    if "--min-score" in sys.argv:
        min_score = float(sys.argv[sys.argv.index("--min-score") + 1])
    
    # evaluate_retrieval()
    evaluate_retrieval(min_score=min_score, mode=mode)
    