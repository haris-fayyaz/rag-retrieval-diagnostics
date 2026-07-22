import pytest
from fastapi.testclient import TestClient

from app.database.models import Base
from app.database.repositories.sqlite_repository import SQLiteDocumentRepository
from app.llm.fake_provider import FakeLLMProvider
from app.main import app, get_llm_provider, get_repository


@pytest.fixture
def client(tmp_path):
    """
    Same pattern as tests/test_persistence.py's fixture, plus a
    FakeLLMProvider override so no test ever calls a real model.
    """
    db_url = f"sqlite:///{tmp_path}/test.db"
    repo = SQLiteDocumentRepository(db_url)
    Base.metadata.create_all(repo.engine)

    provider = FakeLLMProvider(
        response="Employees may claim up to $800 for an approved laptop purchase."
    )

    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_llm_provider] = lambda: provider

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


def test_relevant_question_generates_answer(client):
    """1. Relevant question retrieves chunks and generates an answer."""
    test_client, _, provider = client
    _add_policy_doc(test_client)

    response = test_client.post(
        "/answer", json={"question": "What is the laptop reimbursement limit?"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == provider.response
    assert provider.call_count == 1


def test_no_context_skips_llm_call(client):
    """2. No relevant chunks means the LLM provider is not called."""
    test_client, _, provider = client
    _add_policy_doc(test_client)

    response = test_client.post(
        "/answer", json={"question": "cryptocurrency payment policy", "min_score": 0.99}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] is None
    assert body["message"] == "No relevant information was found in the selected documents."
    assert provider.call_count == 0  # the whole point of this test


def test_response_includes_source_chunk_ids(client):
    """3. Returned response includes source chunk IDs."""
    test_client, _, _ = client
    _add_policy_doc(test_client)

    response = test_client.post(
        "/answer", json={"question": "laptop reimbursement"}
    )

    body = response.json()
    assert len(body["citations"]) == 1
    assert body["citations"][0] == body["retrieved_chunks"][0]["chunk_id"]

def test_citations_never_include_unretrieved_chunks(client):
    """
    5. Returned citations cannot include chunks outside the retrieved set.

    Seeds ONE document that produces TWO distinct chunks (laptop policy,
    parking policy - unrelated topics), then asks a question that only
    matches the laptop chunk with top_k=1. The parking chunk exists in
    the same document and the same DB, so if citations were ever built
    from "all chunks in the matched document" instead of "only what
    retrieval actually returned", this test would catch it.
    """
    test_client, _, _ = client
    test_client.post(
        "/documents",
        json={
            "name": "mixed_policy.txt",
            "text": (
                "Laptop reimbursement is capped at eight hundred dollars per "
                "employee per year for approved business use equipment "
                "purchases only please note.\n\n"
                "Office parking passes are issued by the facilities team "
                "upon request and must be renewed annually every single "
                "year without fail always."
            ),
        },
    )

    response = test_client.post(
        "/answer",
        json={"question": "laptop reimbursement limit", "top_k": 1},
    )

    body = response.json()
    assert len(body["citations"]) == 1
    assert "1_chunk_0" in body["citations"]       # the laptop chunk - expected
    assert "1_chunk_1" not in body["citations"]   # the parking chunk - must never leak in
    
    
def test_invalid_document_id_is_handled(client):
    """4. Invalid document ID is handled - treated as no context, not an error."""
    test_client, _, provider = client
    _add_policy_doc(test_client)

    response = test_client.post(
        "/answer", json={"question": "laptop reimbursement", "document_ids": ["9999"]}
    )

    assert response.status_code == 200
    assert response.json()["answer"] is None
    assert provider.call_count == 0


def test_llm_provider_failure_is_handled_cleanly(client):
    """5. LLM provider failure is handled cleanly - controlled 502, no stack trace."""
    test_client, _, _ = client
    _add_policy_doc(test_client)

    app.dependency_overrides[get_llm_provider] = lambda: FakeLLMProvider(fail=True)

    response = test_client.post("/answer", json={"question": "laptop reimbursement"})

    assert response.status_code == 502
    assert "detail" in response.json()


def test_existing_ask_endpoint_still_works(client):
    """6. Existing /ask endpoint still works, unaffected by /answer."""
    test_client, _, _ = client
    _add_policy_doc(test_client)

    response = test_client.post("/ask", json={"question": "laptop reimbursement", "top_k": 1})

    assert response.status_code == 200
    assert len(response.json()["retrieved_chunks"]) == 1


# -- bonus: remaining error-handling cases from the task's requirement 7 --

def test_empty_question_is_rejected(client):
    test_client, _, provider = client
    _add_policy_doc(test_client)

    response = test_client.post("/answer", json={"question": "   "})

    assert response.status_code == 400
    assert provider.call_count == 0


def test_unsupported_retrieval_mode_is_rejected(client):
    test_client, _, provider = client
    _add_policy_doc(test_client)

    response = test_client.post(
        "/answer", json={"question": "laptop reimbursement", "retrieval_mode": "bogus"}
    )

    assert response.status_code == 400
    assert provider.call_count == 0