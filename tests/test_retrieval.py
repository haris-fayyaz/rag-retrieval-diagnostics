from app.services.retrieval_service import RetrievalService
from app.models import Chunk

def test_retrieval_returns_top_k():
    """Test that retrieval returns only top_k chunks."""
    service = RetrievalService()
    chunks = [
        Chunk(document_id="d1", document_name="doc.txt", chunk_id="c1", score=0, text_preview="laptop reimbursement policy"),
        Chunk(document_id="d1", document_name="doc.txt", chunk_id="c2", score=0, text_preview="vacation days and leave"),
        Chunk(document_id="d1", document_name="doc.txt", chunk_id="c3", score=0, text_preview="health insurance benefits"),
    ]
    result = service.retrieve("laptop reimbursement", chunks, top_k=2)
    assert len(result) == 2

def test_retrieval_ranks_relevant_above_irrelevant():
    """Test that relevant chunks rank higher than irrelevant ones."""
    service = RetrievalService()
    chunks = [
        Chunk(document_id="d1", document_name="doc.txt", chunk_id="c1", score=0, text_preview="laptop reimbursement policy limits"),
        Chunk(document_id="d1", document_name="doc.txt", chunk_id="c2", score=0, text_preview="cats and dogs are animals"),
    ]
    result = service.retrieve("laptop reimbursement", chunks, top_k=2)
    assert result[0].chunk_id == "c1"  # Relevant ranks first
    assert result[0].score > result[1].score
    
    
def test_relevant_question_returns_chunks_above_threshold():
    """Test that relevant questions return chunks when score >= threshold."""
    service = RetrievalService()
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
    service = RetrievalService()
    chunks = [
        Chunk(document_id="d1", document_name="doc.txt", chunk_id="c1", score=0, text_preview="vacation policy"),
    ]
    result = service.retrieve("cryptocurrency payments", chunks, top_k=1)
    filtered = [c for c in result if c.score >= 0.1]
    assert len(filtered) == 0

def test_top_k_respected_after_threshold_filtering():
    """Test that top_k limit is respected after threshold filtering."""
    service = RetrievalService()
    chunks = [
        Chunk(document_id="d1", document_name="doc.txt", chunk_id="c1", score=0, text_preview="laptop reimbursement"),
        Chunk(document_id="d1", document_name="doc.txt", chunk_id="c2", score=0, text_preview="laptop reimbursement policy"),
        Chunk(document_id="d1", document_name="doc.txt", chunk_id="c3", score=0, text_preview="laptop equipment purchase"),
    ]
    result = service.retrieve("laptop", chunks, top_k=2)
    filtered = [c for c in result if c.score >= 0.05]
    assert len(filtered) <= 2