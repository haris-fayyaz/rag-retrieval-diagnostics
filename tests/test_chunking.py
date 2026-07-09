from app.services.chunking_service import chunk_text

def test_document_split_into_chunks():
    """Test that document text is split into chunks."""
    text = "Para 1 with lots of content about reimbursement policies and procedures.\n\nPara 2 with more details about vacation days and leave benefits.\n\nPara 3 with health insurance information and coverage details."
    chunks = chunk_text(text, "doc_1", "test.txt", chunk_size=100)
    assert len(chunks) >= 2
    assert chunks[0].chunk_id == "doc_1_chunk_0"

def test_empty_document_rejected():
    """Test that empty document returns no chunks."""
    chunks = chunk_text("", "doc_1", "test.txt")
    assert len(chunks) == 0
    
    chunks = chunk_text("   ", "doc_1", "test.txt")
    assert len(chunks) == 0