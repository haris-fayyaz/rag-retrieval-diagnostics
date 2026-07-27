import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.database.models import Base
from app.database.repositories.sqlite_repository import SQLiteDocumentRepository
from app.llm.fake_provider import FakeLLMProvider
from app.main import app, get_current_user, get_llm_provider, get_repository


@pytest.fixture
def client(tmp_path):
    """Auth bypassed here - this file tests input validation, not auth."""
    db_url = f"sqlite:///{tmp_path}/test.db"
    repo = SQLiteDocumentRepository(db_url)
    Base.metadata.create_all(repo.engine)

    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_llm_provider] = lambda: FakeLLMProvider(response="ok")
    app.dependency_overrides[get_current_user] = lambda: "test_user"

    yield TestClient(app)

    app.dependency_overrides.clear()


def test_oversized_document_name_rejected(client):
    """9. Oversized document name is rejected."""
    long_name = "x" * (settings.max_document_name_length + 1)
    assert client.post("/documents", json={"name": long_name, "text": "hello"}).status_code == 422


def test_oversized_document_text_rejected(client):
    """9. Oversized document text is rejected."""
    long_text = "x" * (settings.max_document_characters + 1)
    assert client.post("/documents", json={"name": "doc", "text": long_text}).status_code == 422


def test_oversized_question_rejected(client):
    """9. Oversized question is rejected."""
    long_question = "x" * (settings.max_question_characters + 1)
    assert client.post("/answer", json={"question": long_question}).status_code == 422


def test_invalid_top_k_rejected(client):
    """10. top_k outside 1..MAX_TOP_K is rejected."""
    assert client.post("/ask", json={"question": "q", "top_k": 0}).status_code == 422
    assert client.post(
        "/ask", json={"question": "q", "top_k": settings.max_top_k + 1}
    ).status_code == 422


def test_invalid_min_score_rejected(client):
    """10. min_score outside 0.0..1.0 is rejected."""
    assert client.post("/ask", json={"question": "q", "min_score": -0.1}).status_code == 422
    assert client.post("/ask", json={"question": "q", "min_score": 1.1}).status_code == 422


def test_duplicate_document_ids_rejected(client):
    """Extra: document_ids filter with duplicates is rejected."""
    r = client.post("/ask", json={"question": "q", "document_ids": ["doc_1", "doc_1"]})
    assert r.status_code == 422


def test_valid_input_still_accepted(client):
    """Sanity check: validators don't reject legitimate requests."""
    assert client.post(
        "/documents", json={"name": "ok.txt", "text": "A short valid document."}
    ).status_code == 200
    assert client.post(
        "/ask", json={"question": "a valid question", "top_k": 3, "min_score": 0.2}
    ).status_code == 200