import pytest
from fastapi.testclient import TestClient

from app.database.models import Base
from app.database.repositories.sqlite_repository import SQLiteDocumentRepository
from app.llm.fake_provider import FakeLLMProvider
from app.main import app, get_llm_provider, get_repository


@pytest.fixture
def client(tmp_path):
    db_url = f"sqlite:///{tmp_path}/test.db"
    repo = SQLiteDocumentRepository(db_url)
    Base.metadata.create_all(repo.engine)
    provider = FakeLLMProvider(response="The laptop reimbursement limit is $800.")

    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_llm_provider] = lambda: provider

    yield TestClient(app), repo, provider

    app.dependency_overrides.clear()


def _add_policy_doc(test_client):
    test_client.post(
        "/documents",
        json={"name": "it_policy.txt", "text": "Laptop reimbursement is $800 for approved purchases."},
    )


def test_successful_answer_creates_audit_record(client):
    """1. Successful answers create an audit record."""
    test_client, repo, provider = client
    _add_policy_doc(test_client)

    r = test_client.post("/answer", json={"question": "laptop reimbursement"})
    request_id = r.json()["request_id"]

    run = repo.get_answer_run(request_id)
    assert run is not None
    assert run.status == "success"
    assert run.answer == provider.response


def test_no_context_response_creates_audit_record(client):
    """2. No-context responses create an audit record."""
    test_client, repo, _ = client
    _add_policy_doc(test_client)

    r = test_client.post(
        "/answer", json={"question": "cryptocurrency payment policy", "min_score": 0.99}
    )
    request_id = r.json()["request_id"]

    run = repo.get_answer_run(request_id)
    assert run is not None
    assert run.status == "no_context"
    assert run.answer is None


def test_provider_failure_creates_audit_record(client):
    """3. Provider failures create an audit record."""
    test_client, repo, _ = client
    _add_policy_doc(test_client)

    app.dependency_overrides[get_llm_provider] = lambda: FakeLLMProvider(fail=True)
    r = test_client.post("/answer", json={"question": "laptop reimbursement"})
    request_id = r.json()["detail"]["request_id"]

    run = repo.get_answer_run(request_id)
    assert run is not None
    assert run.status == "provider_error"
    assert run.answer is None


def test_retrieved_chunk_ids_and_citations_are_stored(client):
    """4. Retrieved chunk IDs and citations are stored."""
    test_client, repo, _ = client
    _add_policy_doc(test_client)

    r = test_client.post("/answer", json={"question": "laptop reimbursement"})
    body = r.json()
    request_id = body["request_id"]

    run = repo.get_answer_run(request_id)
    assert run.retrieved_chunk_ids == [c["chunk_id"] for c in body["retrieved_chunks"]]
    assert run.citations == body["citations"]


def test_audit_record_fetchable_by_request_id(client):
    """5. Audit record can be fetched by request ID."""
    test_client, _, _ = client
    _add_policy_doc(test_client)

    r = test_client.post("/answer", json={"question": "laptop reimbursement"})
    request_id = r.json()["request_id"]

    r2 = test_client.get(f"/answer-runs/{request_id}")
    assert r2.status_code == 200
    assert r2.json()["request_id"] == request_id
    assert r2.json()["question"] == "laptop reimbursement"


def test_unknown_request_id_returns_404(client):
    """6. Unknown request ID returns 404."""
    test_client, _, _ = client

    r = test_client.get("/answer-runs/does-not-exist")
    assert r.status_code == 404


def test_fake_provider_runs_remain_deterministic(client):
    """
    7. Fake-provider runs remain deterministic.

    Same question, same document, same FakeLLMProvider - run twice, the
    audit records for retrieval and generation must match exactly (aside
    from request_id/timing, which are expected to differ per call).
    """
    test_client, repo, _ = client
    _add_policy_doc(test_client)

    r1 = test_client.post("/answer", json={"question": "laptop reimbursement"})
    r2 = test_client.post("/answer", json={"question": "laptop reimbursement"})

    run1 = repo.get_answer_run(r1.json()["request_id"])
    run2 = repo.get_answer_run(r2.json()["request_id"])

    assert run1.answer == run2.answer
    assert run1.retrieved_chunk_ids == run2.retrieved_chunk_ids
    assert run1.citations == run2.citations
    assert run1.status == run2.status == "success"