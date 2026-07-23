from app.core.config import Settings
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
    
    
def test_long_paragraph_is_not_truncated():
    """
    1. A long paragraph is not truncated.

    One paragraph, ~1500 chars, no blank-line breaks - forces the
    sentence/word-safe fallback path in _split_into_units. Every distinct
    word in the source must still appear somewhere across the chunks.
    """
    sentences = [f"This is sentence number {i} about the company policy." for i in range(30)]
    text = " ".join(sentences)  # single paragraph, well over chunk_size

    chunks = chunk_text(text, "1", "doc.txt", chunk_size=400, chunk_overlap=50)

    recovered = " ".join(c.text_preview for c in chunks)
    for word in set(text.split()):
        assert word in recovered, f"'{word}' was lost during chunking"


def test_end_of_document_text_is_present():
    """
    2. Text from the end of a document is still present in the generated
    chunks.

    Old behavior (hard [:200] slice on the whole document) silently
    dropped everything past the first 200 characters - a marker placed at
    the very end would never have survived. This proves it now does.
    """
    text = ("Filler content. " * 100) + "END_OF_DOCUMENT_MARKER_XYZ."

    chunks = chunk_text(text, "1", "doc.txt", chunk_size=300, chunk_overlap=30)

    all_text = " ".join(c.text_preview for c in chunks)
    assert "END_OF_DOCUMENT_MARKER_XYZ" in all_text


def test_overlap_exists_between_consecutive_chunks():
    """
    3. Overlap exists between consecutive chunks.

    Forces multiple chunks, then checks that the tail words of one chunk
    reappear at the head of the next - proving shared context actually
    carries across the boundary, not just that both chunks exist.
    """
    words = [f"word{i}" for i in range(200)]
    text = " ".join(words)

    chunks = chunk_text(text, "1", "doc.txt", chunk_size=300, chunk_overlap=60)
    assert len(chunks) >= 2, "test needs at least 2 chunks to check overlap"

    for i in range(len(chunks) - 1):
        tail_words = set(chunks[i].text_preview.split()[-5:])
        head_words = set(chunks[i + 1].text_preview.split()[:5])
        assert tail_words & head_words, (
            f"no shared words between chunk {i} tail and chunk {i + 1} head"
        )


def test_invalid_chunk_configuration_is_rejected(monkeypatch):
    """4. Invalid chunk configuration is rejected."""
    monkeypatch.setenv("CHUNK_SIZE", "0")
    monkeypatch.setenv("CHUNK_OVERLAP", "0")
    try:
        Settings()
        assert False, "CHUNK_SIZE=0 should have raised"
    except ValueError:
        pass

    monkeypatch.setenv("CHUNK_SIZE", "800")
    monkeypatch.setenv("CHUNK_OVERLAP", "-1")
    try:
        Settings()
        assert False, "negative CHUNK_OVERLAP should have raised"
    except ValueError:
        pass

    monkeypatch.setenv("CHUNK_SIZE", "800")
    monkeypatch.setenv("CHUNK_OVERLAP", "800")
    try:
        Settings()
        assert False, "CHUNK_OVERLAP == CHUNK_SIZE should have raised"
    except ValueError:
        pass