import json
from app.services.document_store import DocumentStore
from app.services.chunking_service import chunk_text
from app.services.retrieval_service import RetrievalService
from app.services.semantic_retrieval_service import SemanticRetrievalService


def load_json(filepath):
    """Load JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def evaluate_retrieval(min_score=0.0, mode="tfidf"):
    """Run retrieval evaluation on test questions."""
    
    # Load data
    docs_data = load_json("eval/sample_documents.json")
    questions_data = load_json("eval/eval_questions.json")
    
    # Initialize services
    doc_store = DocumentStore()
    
    # Select the retrival mode
    if mode == "semantic":
        retrieval_service = SemanticRetrievalService()
    else:
        retrieval_service = RetrievalService()
    
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
        retrieved = retrieval_service.retrieve(question, all_chunks, top_k=1)
        
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
    