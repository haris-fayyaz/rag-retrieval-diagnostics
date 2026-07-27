import pytest
from fastapi.testclient import TestClient

from app.database.models import Base
from app.database.repositories.sqlite_repository import SQLiteDocumentRepository
from app.llm.fake_provider import FakeLLMProvider
from app.main import app, get_llm_provider, get_repository, get_current_user


@pytest.fixture
def client(tmp_path):
    db_url = f"sqlite:///{tmp_path}/test.db"
    repo = SQLiteDocumentRepository(db_url)
    Base.metadata.create_all(repo.engine)
    provider = FakeLLMProvider(response="Answer text.")

    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_llm_provider] = lambda: provider
    app.dependency_overrides[get_current_user] = lambda: "test_user"  # bypass auth, not what this file tests
    
    yield TestClient(app), repo, provider

    app.dependency_overrides.clear()


def test_reindex_replaces_chunks_without_duplicates(client):
    """5. Re-indexing replaces old chunks without creating duplicates."""
    test_client, repo, _ = client
    text = "Sentence one about policy. " * 40  # forces multiple chunks
    r = test_client.post("/documents", json={"name": "doc.txt", "text": text})
    doc_id = r.json()["document_id"]

    r2 = test_client.post(f"/documents/{doc_id}/reindex")
    assert r2.status_code == 200
    body = r2.json()

    chunks = repo.get_chunks([doc_id])
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))          # no duplicates
    assert len(ids) == body["new_chunk_count"]


def test_failed_reindex_leaves_previous_chunks_intact(client):
    """6. Failed re-indexing leaves the previous chunks intact."""
    test_client, repo, _ = client
    r = test_client.post("/documents", json={"name": "doc.txt", "text": "Some policy text."})
    doc_id = r.json()["document_id"]

    before = repo.get_chunks([doc_id])

    def broken_chunker(text, document_id, document_name):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        repo.reindex_document(doc_id, broken_chunker)

    after = repo.get_chunks([doc_id])
    assert [c.chunk_id for c in before] == [c.chunk_id for c in after]


def test_retrieval_and_answer_work_after_reindex(client):
    """7. Retrieval and /answer still work after re-indexing."""
    test_client, _, provider = client
    r = test_client.post(
        "/documents",
        json={"name": "it_policy.txt", "text": "Laptop reimbursement limit is $800."},
    )
    doc_id = r.json()["document_id"]

    test_client.post(f"/documents/{doc_id}/reindex")

    ask_r = test_client.post("/ask", json={"question": "laptop reimbursement"})
    assert ask_r.status_code == 200
    assert len(ask_r.json()["retrieved_chunks"]) >= 1

    answer_r = test_client.post("/answer", json={"question": "laptop reimbursement"})
    assert answer_r.status_code == 200
    assert answer_r.json()["answer"] == provider.response