import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.database.models import Base
from app.database.repositories.sqlite_repository import SQLiteDocumentRepository
from app.llm.exceptions import LLMTimeoutError
from app.llm.fake_provider import FakeLLMProvider
from app.main import app, get_llm_provider, get_repository, get_current_user


@pytest.fixture
def client(tmp_path):
    """Same pattern as tests/test_answer.py's fixture - fresh temp DB and
    a FakeLLMProvider per test, no real network/model involved."""
    db_url = f"sqlite:///{tmp_path}/test.db"
    repo = SQLiteDocumentRepository(db_url)
    Base.metadata.create_all(repo.engine)

    provider = FakeLLMProvider(
        response="Employees may claim up to $800 for an approved laptop purchase."
    )

    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_llm_provider] = lambda: provider
    app.dependency_overrides[get_current_user] = lambda: "test_user"  # bypass auth, not what this file tests

    yield TestClient(app), repo, provider

    app.dependency_overrides.clear()


def _add_policy_doc(test_client):
    test_client.post(
        "/documents",
        json={
            "name": "it_policy.txt",
            "text": "Employees may claim laptop reimbursement up to $800 for an approved purchase.",
        },
    )


def test_successful_response_includes_request_id_and_metadata(client):
    """1. Successful response includes request ID and timing metadata."""
    test_client, _, _ = client
    _add_policy_doc(test_client)

    response = test_client.post("/answer", json={"question": "laptop reimbursement"})

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"]  # non-empty string
    metadata = body["metadata"]
    assert metadata["retrieval_ms"] is not None
    assert metadata["generation_ms"] is not None
    assert metadata["total_ms"] is not None
    assert metadata["retrieved_chunk_count"] == 1
    assert metadata["retrieval_mode"] == "tfidf"
    assert metadata["provider"] == "fake"


def test_temporary_failure_retries_then_succeeds(client, monkeypatch):
    """2. Temporary provider failure retries and then succeeds."""
    test_client, _, _ = client
    _add_policy_doc(test_client)

    # Mutate the shared settings singleton's attribute (not reassign the
    # name) - app.main and answer_service both hold a reference to the
    # SAME object, so this is visible to both without re-importing.
    monkeypatch.setattr(settings, "llm_max_retries", 2)

    flaky_provider = FakeLLMProvider(response="recovered answer", fail_times=1)
    app.dependency_overrides[get_llm_provider] = lambda: flaky_provider

    response = test_client.post("/answer", json={"question": "laptop reimbursement"})

    assert response.status_code == 200
    assert response.json()["answer"] == "recovered answer"
    assert flaky_provider.call_count == 2  # failed once, succeeded on the retry


def test_repeated_failure_returns_controlled_error(client, monkeypatch):
    """3. Repeated provider failure returns a controlled error - never a
    raw stack trace, and stops after the configured retry count."""
    test_client, _, _ = client
    _add_policy_doc(test_client)

    monkeypatch.setattr(settings, "llm_max_retries", 2)
    always_failing = FakeLLMProvider(fail=True)
    app.dependency_overrides[get_llm_provider] = lambda: always_failing

    response = test_client.post("/answer", json={"question": "laptop reimbursement"})

    assert response.status_code == 502
    assert "request_id" in response.json()["detail"]
    assert always_failing.call_count == 3  # 1 initial attempt + 2 retries, then stop


def test_timeout_is_handled_cleanly(client, monkeypatch):
    """4. Timeout is handled cleanly. LLMTimeoutError is a subtype of
    LLMTemporaryError, so it's retried the same way - and once retries
    are exhausted it still returns a controlled 502, not a stack trace."""
    test_client, _, _ = client
    _add_policy_doc(test_client)

    monkeypatch.setattr(settings, "llm_max_retries", 1)
    timing_out = FakeLLMProvider(fail=True, error=LLMTimeoutError)
    app.dependency_overrides[get_llm_provider] = lambda: timing_out

    response = test_client.post("/answer", json={"question": "laptop reimbursement"})

    assert response.status_code == 502
    assert timing_out.call_count == 2  # 1 initial + 1 retry
    assert "request_id" in response.json()["detail"]


def test_no_context_does_not_call_or_retry_llm(client):
    """5. No-context response does not call or retry the LLM."""
    test_client, _, provider = client
    _add_policy_doc(test_client)

    response = test_client.post(
        "/answer", json={"question": "cryptocurrency payment policy", "min_score": 0.99}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] is None
    assert provider.call_count == 0
    assert body["metadata"]["generation_ms"] is None


def test_timing_values_are_non_negative(client):
    """6. Retrieval and generation timing values are non-negative."""
    test_client, _, _ = client
    _add_policy_doc(test_client)

    response = test_client.post("/answer", json={"question": "laptop reimbursement"})

    metadata = response.json()["metadata"]
    assert metadata["retrieval_ms"] >= 0
    assert metadata["generation_ms"] >= 0
    assert metadata["total_ms"] >= 0
    assert metadata["total_ms"] >= metadata["retrieval_ms"]


def test_existing_ask_and_answer_still_work(client):
    """7. Existing /ask and /answer behavior still works."""
    test_client, _, _ = client
    _add_policy_doc(test_client)

    ask_response = test_client.post("/ask", json={"question": "laptop reimbursement", "top_k": 1})
    assert ask_response.status_code == 200
    assert len(ask_response.json()["retrieved_chunks"]) == 1

    answer_response = test_client.post("/answer", json={"question": "laptop reimbursement"})
    assert answer_response.status_code == 200
    assert answer_response.json()["citations"] == ["1_chunk_0"]