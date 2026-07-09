#!/usr/bin/env python3
"""
Retrieval Evaluation Script

Loads sample documents and evaluation questions, runs retrieval,
and measures accuracy by comparing top results to expected documents.
"""

import json
import sys
from pathlib import Path
from typing import Optional, List, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.document_store import DocumentStore
from app.services.chunking_service import chunk_text
from app.services.retrieval_service import RetrievalService


def load_sample_documents(eval_dir: Path) -> dict:
    """Load sample documents from JSON."""
    with open(eval_dir / "sample_documents.json", "r") as f:
        return json.load(f)


def load_eval_questions(eval_dir: Path) -> dict:
    """Load evaluation questions from JSON."""
    with open(eval_dir / "eval_questions.json", "r") as f:
        return json.load(f)


def setup_retrieval_system(sample_docs: dict) -> Tuple[DocumentStore, RetrievalService, dict]:
    """
    Initialize document store and retrieval service with sample documents.
    
    Returns:
        - document store
        - retrieval service
        - mapping of doc_id to document_name for lookup
    """
    doc_store = DocumentStore()
    retrieval_service = RetrievalService()
    doc_id_to_name = {}
    
    for doc_info in sample_docs["documents"]:
        doc_name = doc_info["name"]
        doc_text = doc_info["text"]
        
        # Add document to store
        response = doc_store.add_document(doc_name, doc_text)
        doc_id = response.document_id
        
        # Chunk document
        chunks = chunk_text(doc_text, doc_id, doc_name)
        doc_store.update_chunks(doc_id, chunks)
        
        # Store mapping for later lookup
        doc_id_to_name[doc_id] = doc_name
    
    return doc_store, retrieval_service, doc_id_to_name


def evaluate_retrieval(
    doc_store: DocumentStore,
    retrieval_service: RetrievalService,
    doc_id_to_name: dict,
    questions: dict
) -> Tuple[List[dict], int, int]:
    """
    Evaluate retrieval for all questions.
    
    Returns:
        - list of result dicts with question, expected, top_result, passed
        - total questions
        - passed count
    """
    results = []
    passed_count = 0
    
    for q_item in questions["questions"]:
        question = q_item["question"]
        expected_doc = q_item["expected_document"]
        
        # Gather all chunks from all documents
        all_chunks = []
        for doc_id, doc in doc_store.documents.items():
            all_chunks.extend(doc["chunks"])
        
        # Retrieve top-1
        retrieved = retrieval_service.retrieve(question, all_chunks, top_k=1)
        
        # Extract retrieved document name
        if retrieved:
            top_result = doc_id_to_name.get(retrieved[0].document_id, "unknown")
            top_score = retrieved[0].score
        else:
            top_result = None
            top_score = 0.0
        
        # Determine pass/fail
        if expected_doc is None:
            # Unanswerable or vague questions should not confidently retrieve
            # For now, we mark as "failed" if something was retrieved
            passed = False
        else:
            # Expected document should match top result
            passed = (top_result == expected_doc)
        
        if passed:
            passed_count += 1
        
        results.append({
            "question": question,
            "expected": expected_doc,
            "top_result": top_result,
            "score": round(top_score, 4),
            "passed": passed
        })
    
    return results, len(questions["questions"]), passed_count


def print_results_table(results: List[dict]) -> None:
    """Print formatted results table."""
    print("\n" + "=" * 120)
    print("RETRIEVAL EVALUATION RESULTS")
    print("=" * 120)
    
    # Column widths
    q_width = 45
    exp_width = 15
    top_width = 15
    score_width = 10
    pass_width = 6
    
    # Header
    header = f"{'Question':<{q_width}} {'Expected':<{exp_width}} {'Top Result':<{top_width}} {'Score':<{score_width}} {'Pass'}"
    print(header)
    print("-" * 120)
    
    # Rows
    for result in results:
        q_short = result["question"][:q_width - 3] + "..." if len(result["question"]) > q_width - 3 else result["question"]
        exp = result["expected"] or "None"
        top = result["top_result"] or "None"
        score = f"{result['score']:.4f}"
        passed = "✓" if result["passed"] else "✗"
        
        row = f"{q_short:<{q_width}} {exp:<{exp_width}} {top:<{top_width}} {score:<{score_width}} {passed}"
        print(row)
    
    print("=" * 120)


def print_summary_metrics(total: int, passed: int) -> None:
    """Print summary statistics."""
    failed = total - passed
    accuracy = (passed / total * 100) if total > 0 else 0.0
    
    print("\n" + "=" * 40)
    print("SUMMARY METRICS")
    print("=" * 40)
    print(f"Total questions:  {total}")
    print(f"Passed:           {passed}")
    print(f"Failed:           {failed}")
    print(f"Accuracy:         {accuracy:.1f}%")
    print("=" * 40)


def main():
    """Main evaluation workflow."""
    eval_dir = Path(__file__).parent.parent / "eval"
    
    # Validate directories exist
    if not eval_dir.exists():
        print(f"Error: {eval_dir} directory not found")
        sys.exit(1)
    
    print("Loading sample documents and questions...")
    sample_docs = load_sample_documents(eval_dir)
    questions = load_eval_questions(eval_dir)
    
    print(f"Loaded {len(sample_docs['documents'])} documents and {len(questions['questions'])} questions")
    
    print("Setting up retrieval system...")
    doc_store, retrieval_service, doc_id_to_name = setup_retrieval_system(sample_docs)
    
    print("Running retrieval evaluation...")
    results, total, passed = evaluate_retrieval(doc_store, retrieval_service, doc_id_to_name, questions)
    
    # Print results
    print_results_table(results)
    print_summary_metrics(total, passed)


if __name__ == "__main__":
    main()
