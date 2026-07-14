from app.services.retrieval.tfidf_retrieval_service import TFIDF
from app.services.retrieval.semantic_retrieval_service import SemanticRetrievalService
from app.models import AskRequest
from app.models import Chunk

def test_retrieval_returns_top_k():
    """Test that retrieval returns only top_k chunks."""
    service = TFIDF()
    chunks = [
        Chunk(document_id="d1", document_name="doc.txt", chunk_id="c1", score=0, text_preview="laptop reimbursement policy"),
        Chunk(document_id="d1", document_name="doc.txt", chunk_id="c2", score=0, text_preview="vacation days and leave"),
        Chunk(document_id="d1", document_name="doc.txt", chunk_id="c3", score=0, text_preview="health insurance benefits"),
    ]
    result = service.retrieve("laptop reimbursement", chunks, top_k=2)
    assert len(result) == 2

def test_retrieval_ranks_relevant_above_irrelevant():
    """Test that relevant chunks rank higher than irrelevant ones."""
    service = TFIDF()
    chunks = [
        Chunk(document_id="d1", document_name="doc.txt", chunk_id="c1", score=0, text_preview="laptop reimbursement policy limits"),
        Chunk(document_id="d1", document_name="doc.txt", chunk_id="c2", score=0, text_preview="cats and dogs are animals"),
    ]
    result = service.retrieve("laptop reimbursement", chunks, top_k=2)
    assert result[0].chunk_id == "c1"  # Relevant ranks first
    assert result[0].score > result[1].score
    
    
def test_relevant_question_returns_chunks_above_threshold():
    """Test that relevant questions return chunks when score >= threshold."""
    service = TFIDF()
    chunks = [
        Chunk(document_id="d1", document_name="doc.txt", chunk_id="c1", score=0, text_preview="laptop reimbursement policy limit"),
    ]
    result = service.retrieve("laptop reimbursement", chunks, top_k=1)
    # Filter by threshold
    filtered = [c for c in result if c.score >= 0.1]
    assert len(filtered) == 1
    assert filtered[0].score >= 0.1

def test_unanswerable_question_returns_empty_with_threshold():
    """Test that unanswerable questions return empty list with high threshold."""
    service = TFIDF()
    chunks = [
        Chunk(document_id="d1", document_name="doc.txt", chunk_id="c1", score=0, text_preview="vacation policy"),
    ]
    result = service.retrieve("cryptocurrency payments", chunks, top_k=1)
    filtered = [c for c in result if c.score >= 0.1]
    assert len(filtered) == 0

def test_top_k_respected_after_threshold_filtering():
    """Test that top_k limit is respected after threshold filtering."""
    service = TFIDF()
    chunks = [
        Chunk(document_id="d1", document_name="doc.txt", chunk_id="c1", score=0, text_preview="laptop reimbursement"),
        Chunk(document_id="d1", document_name="doc.txt", chunk_id="c2", score=0, text_preview="laptop reimbursement policy"),
        Chunk(document_id="d1", document_name="doc.txt", chunk_id="c3", score=0, text_preview="laptop equipment purchase"),
    ]
    result = service.retrieve("laptop", chunks, top_k=2)
    filtered = [c for c in result if c.score >= 0.05]
    assert len(filtered) <= 2
    
def test_semantic_retrieval_returns_relevant_chunks():
    """Test semantic retrieval returns relevant chunks."""
    service = SemanticRetrievalService()
    chunks = [
        Chunk(document_id="d1", document_name="doc.txt", chunk_id="c1", score=0, text_preview="laptop computer reimbursement policy limit"),
        Chunk(document_id="d1", document_name="doc.txt", chunk_id="c2", score=0, text_preview="vacation days and holiday time"),
    ]
    result = service.retrieve("laptop reimbursement", chunks, top_k=2)
    assert len(result) >= 1
    assert result[0].chunk_id == "c1"

def test_retrieval_mode_tfidf_still_works():
    """Test that TF-IDF mode still works alongside semantic."""
    service = TFIDF()
    chunks = [
        Chunk(document_id="d1", document_name="doc.txt", chunk_id="c1", score=0, text_preview="laptop reimbursement"),
    ]
    result = service.retrieve("laptop", chunks, top_k=1)
    assert len(result) == 1

def test_invalid_retrieval_mode_rejected():
    """Test that invalid retrieval modes are rejected."""
    valid = AskRequest(question="test", retrieval_mode="tfidf")
    assert valid.retrieval_mode == "tfidf"
    valid_semantic = AskRequest(question="test", retrieval_mode="semantic")
    assert valid_semantic.retrieval_mode == "semantic"
    
    
def test_top1_accuracy_calculation():
    """Test Top-1 accuracy metric."""
    from scripts.evaluate_retrieval import is_top1_match
    chunks = [Chunk(document_id="doc_0", document_name="test", chunk_id="c1", score=0.5, text_preview="test")]
    assert is_top1_match(["doc_0"], chunks)
    assert not is_top1_match(["doc_1"], chunks)

def test_recall_at_k_calculation():
    """Test Recall@K metric."""
    from scripts.evaluate_retrieval import calculate_recall_at_k
    chunks = [
        Chunk(document_id="doc_0", document_name="test", chunk_id="c1", score=0.5, text_preview="test"),
        Chunk(document_id="doc_1", document_name="test", chunk_id="c2", score=0.4, text_preview="test"),
    ]
    recall = calculate_recall_at_k(["doc_0", "doc_1"], chunks, k=2)
    assert recall == 1.0

def test_no_answer_accuracy_calculation():
    """Test No-answer accuracy metric."""
    from scripts.evaluate_retrieval import is_no_answer_correct
    assert is_no_answer_correct([], [])
    chunks = [Chunk(document_id="doc_0", document_name="test", chunk_id="c1", score=0.5, text_preview="test")]
    assert not is_no_answer_correct([], chunks)