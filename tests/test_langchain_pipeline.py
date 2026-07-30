import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.chat_models import SimpleChatModel

from app.database.models import Base
from app.database.repositories.sqlite_repository import SQLiteDocumentRepository
from app.llm.exceptions import LLMPermanentError
from app.llm.fake_provider import FakeLLMProvider
from app.main import app, get_current_user, get_langchain_model, get_llm_provider, get_repository


class CountingFakeChatModel(SimpleChatModel):
    """
    Same purpose as FakeLLMProvider.call_count for the custom pipeline:
    a deterministic, no-network chat model that also proves how many
    times it was actually invoked.
    """
    response: str = "This is a fake generated answer via LangChain."
    call_count: int = 0

    @property
    def _llm_type(self) -> str:
        return "counting-fake-chat-model"

    def _call(self, messages, stop=None, run_manager=None, **kwargs) -> str:
        self.call_count += 1
        return self.response


class FailingChatModel(SimpleChatModel):
    """Raises on every call - proves a langchain-path failure gets
    translated into the same controlled error as the custom path."""

    @property
    def _llm_type(self) -> str:
        return "failing-chat-model"

    def _call(self, messages, stop=None, run_manager=None, **kwargs) -> str:
        raise LLMPermanentError("Simulated langchain provider failure")


@pytest.fixture
def client(tmp_path):
    """Same pattern as test_answer.py's fixture, plus a controllable
    fake chat model override for the langchain pipeline."""
    db_url = f"sqlite:///{tmp_path}/test.db"
    repo = SQLiteDocumentRepository(db_url)
    Base.metadata.create_all(repo.engine)

    provider = FakeLLMProvider(response="Employees may claim up to $800 for an approved laptop purchase.")
    langchain_model = CountingFakeChatModel()

    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_llm_provider] = lambda: provider
    app.dependency_overrides[get_langchain_model] = lambda: langchain_model
    app.dependency_overrides[get_current_user] = lambda: "test_user"

    yield TestClient(app), repo, provider, langchain_model

    app.dependency_overrides.clear()


def _add_policy_doc(test_client):
    test_client.post(
        "/documents",
        json={
            "name": "it_policy.txt",
            "text": "Employees may claim laptop reimbursement up to $800 for an approved purchase.",
        },
    )


def test_default_pipeline_mode_is_custom(client):
    """1. Default mode remains custom."""
    test_client, _, provider, langchain_model = client
    _add_policy_doc(test_client)

    response = test_client.post("/answer", json={"question": "laptop reimbursement limit"})

    assert response.status_code == 200
    assert response.json()["metadata"]["provider"] == "fake"
    assert provider.call_count == 1
    assert langchain_model.call_count == 0


def test_langchain_mode_generates_an_answer(client):
    """2. LangChain mode generates an answer."""
    test_client, _, provider, langchain_model = client
    _add_policy_doc(test_client)

    response = test_client.post(
        "/answer", json={"question": "laptop reimbursement limit", "pipeline_mode": "langchain"}
    )

    assert response.status_code == 200
    assert response.json()["answer"] == langchain_model.response
    assert langchain_model.call_count == 1
    assert provider.call_count == 0


def test_both_modes_use_the_same_retrieved_chunks(client):
    """3. Both modes use the same retrieved chunks."""
    test_client, _, _, _ = client
    _add_policy_doc(test_client)

    r_custom = test_client.post("/answer", json={"question": "laptop reimbursement limit", "pipeline_mode": "custom"})
    r_lc = test_client.post("/answer", json={"question": "laptop reimbursement limit", "pipeline_mode": "langchain"})

    custom_chunks = [c["chunk_id"] for c in r_custom.json()["retrieved_chunks"]]
    lc_chunks = [c["chunk_id"] for c in r_lc.json()["retrieved_chunks"]]
    assert custom_chunks == lc_chunks


def test_both_modes_return_citations_from_retrieved_set(client):
    """4. Both modes return citations from the retrieved set."""
    test_client, _, _, _ = client
    _add_policy_doc(test_client)

    for mode in ("custom", "langchain"):
        body = test_client.post(
            "/answer", json={"question": "laptop reimbursement limit", "pipeline_mode": mode}
        ).json()
        retrieved_ids = {c["chunk_id"] for c in body["retrieved_chunks"]}
        assert len(body["citations"]) > 0
        assert set(body["citations"]).issubset(retrieved_ids)


def test_no_context_skips_model_execution_on_langchain_path(client):
    """5. No-context skips model execution, langchain mode included."""
    test_client, _, _, langchain_model = client
    _add_policy_doc(test_client)

    response = test_client.post(
        "/answer",
        json={"question": "cryptocurrency payment policy", "min_score": 0.99, "pipeline_mode": "langchain"},
    )

    assert response.status_code == 200
    assert response.json()["answer"] is None
    assert langchain_model.call_count == 0


def test_invalid_pipeline_mode_is_rejected(client):
    """6. Invalid pipeline_mode value is rejected."""
    test_client, _, provider, langchain_model = client
    _add_policy_doc(test_client)

    response = test_client.post("/answer", json={"question": "laptop reimbursement", "pipeline_mode": "bogus"})

    assert response.status_code == 422
    assert provider.call_count == 0
    assert langchain_model.call_count == 0


def test_langchain_provider_failure_is_handled_cleanly(client):
    """7. Provider failures on the langchain path stay controlled (502, not a raw 500)."""
    test_client, _, _, _ = client
    _add_policy_doc(test_client)

    app.dependency_overrides[get_langchain_model] = lambda: FailingChatModel()

    response = test_client.post(
        "/answer", json={"question": "laptop reimbursement", "pipeline_mode": "langchain"}
    )

    assert response.status_code == 502
    assert "detail" in response.json()


def test_audit_record_stores_pipeline_mode(client):
    """8. Audit record stores the pipeline mode."""
    test_client, _, _, _ = client
    _add_policy_doc(test_client)

    response = test_client.post(
        "/answer", json={"question": "laptop reimbursement limit", "pipeline_mode": "langchain"}
    )
    request_id = response.json()["request_id"]

    audit = test_client.get(f"/answer-runs/{request_id}")

    assert audit.status_code == 200
    assert audit.json()["pipeline_mode"] == "langchain"


def test_audit_record_defaults_to_custom_pipeline_mode(client):
    """8b. Audit record for a default (no pipeline_mode) request stores 'custom'."""
    test_client, _, _, _ = client
    _add_policy_doc(test_client)

    response = test_client.post("/answer", json={"question": "laptop reimbursement limit"})
    request_id = response.json()["request_id"]

    audit = test_client.get(f"/answer-runs/{request_id}")

    assert audit.json()["pipeline_mode"] == "custom"