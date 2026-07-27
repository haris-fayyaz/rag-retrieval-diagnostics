import pytest
from fastapi.testclient import TestClient

from app.database.models import Base
from app.main import app, get_repository, get_current_user
from app.models import Chunk
from app.database.repositories.sqlite_repository import SQLiteDocumentRepository


@pytest.fixture
def client(tmp_path):
    """
    A TestClient wired to a throwaway SQLite file per test (via tmp_path),
    with the app's repository dependency overridden to point at it.

    Tables are created directly from ORM metadata rather than by running
    `alembic upgrade head` - Alembic is for evolving a real, long-lived
    database; tests just need a fresh schema fast and in isolation.
    """
    db_url = f"sqlite:///{tmp_path}/test.db"
    repo = SQLiteDocumentRepository(db_url)
    Base.metadata.create_all(repo.engine)

    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: "test_user"  # bypass auth, not what this file tests
    yield TestClient(app), repo, db_url
    app.dependency_overrides.clear()


def test_document_and_chunks_are_persisted(client):
    """1. A document and its chunks are persisted."""
    test_client, repo, _ = client

    response = test_client.post(
        "/documents",
        json={
            "name": "policy.txt",
            "text": "Vacation days are generous.\n\nSick leave rules apply too.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["chunk_count"] >= 1

    stored = repo.get_document(body["document_id"])
    assert stored is not None
    assert stored["name"] == "policy.txt"
    assert len(stored["chunks"]) == body["chunk_count"]


def test_data_readable_from_new_repository_instance(client):
    """2. Data can be read using a new repository/session instance."""
    test_client, _, db_url = client

    response = test_client.post(
        "/documents",
        json={"name": "handbook.txt", "text": "Remote work policy details here."},
    )
    doc_id = response.json()["document_id"]

    # A brand new repository instance - its own engine and its own session -
    # pointed at the same database file.
    fresh_repo = SQLiteDocumentRepository(db_url)

    documents = fresh_repo.list_documents()
    assert any(d.document_id == doc_id and d.name == "handbook.txt" for d in documents)

    chunks = fresh_repo.get_chunks([doc_id])
    assert len(chunks) == 1
    assert "Remote work policy" in chunks[0].text_preview


def test_ask_retrieves_from_persisted_chunks(client):
    """3. Retrieval works using persisted chunks."""
    test_client, _, _ = client

    test_client.post(
        "/documents",
        json={"name": "policy.txt", "text": "Employees get 20 vacation days per year."},
    )

    response = test_client.post(
        "/ask",
        json={"question": "vacation days", "top_k": 1, "retrieval_mode": "tfidf"},
    )
    assert response.status_code == 200
    retrieved = response.json()["retrieved_chunks"]
    assert len(retrieved) == 1
    assert "vacation" in retrieved[0]["text_preview"].lower()


def test_invalid_document_id_is_handled(client):
    """4. An invalid document ID is handled correctly."""
    test_client, repo, _ = client

    # Neither a non-numeric ID nor an unknown numeric ID should raise -
    # both are treated as "not found".
    assert repo.get_document("not-a-real-id") is None
    assert repo.get_document("9999") is None
    assert repo.get_chunks(["9999"]) == []

    response = test_client.post(
        "/ask", json={"question": "anything", "document_ids": ["9999"]}
    )
    assert response.status_code == 404


def test_empty_document_is_rejected(client):
    """5. Empty documents remain rejected."""
    test_client, repo, _ = client

    response = test_client.post("/documents", json={"name": "empty.txt", "text": "   "})
    assert response.status_code == 422

    with pytest.raises(ValueError):
        repo.add_document("empty.txt", "   ")


def test_save_chunks_for_unknown_document_raises(client):
    """Bonus: saving chunks against a document that doesn't exist fails
    cleanly and leaves nothing behind, instead of silently orphaning rows."""
    _, repo, _ = client

    bogus_chunk = [
        Chunk(document_id="9999", document_name="x", chunk_id="9999_chunk_0", score=0.0, text_preview="text")
    ]
    with pytest.raises(ValueError):
        repo.save_chunks("9999", bogus_chunk)

    assert repo.get_chunks(["9999"]) == []
    
    
def test_document_creation_is_transactional(client):
    """
    Task 15 requirement #9: document and chunk creation happen in one
    transaction - if chunking/chunk-saving fails, no empty/orphaned
    document is left behind, and the session rolls back cleanly.

    Simulates a chunker failure (any exception during chunk generation
    or insertion) and confirms the document count is unchanged - proving
    create_document_with_chunks() is atomic, not "create doc, then
    separately try to add chunks".
    """
    _, repo, _ = client

    def broken_chunker(text, document_id, document_name):
        raise RuntimeError("simulated chunking failure")

    before = repo.list_documents()

    with pytest.raises(RuntimeError):
        repo.create_document_with_chunks("broken.txt", "some text", broken_chunker)

    after = repo.list_documents()
    assert before == after  # nothing was persisted - no orphaned document

    # A working chunker afterward proves the session/engine is still
    # healthy - i.e. the failed transaction didn't leave the connection
    # in a broken state (rolled back and closed correctly).
    from app.services.chunking_service import chunk_text
    response = repo.create_document_with_chunks("policy.txt", "Real content here.", chunk_text)
    assert response.chunk_count == 1
    assert len(repo.list_documents()) == len(before) + 1