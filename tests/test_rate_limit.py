import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.database.models import Base
from app.database.repositories.sqlite_repository import SQLiteDocumentRepository
from app.llm.fake_provider import FakeLLMProvider
from app.main import app, get_llm_provider, get_repository


@pytest.fixture
def client(tmp_path):
    """
    Auth is real here (not bypassed) - rate limits are keyed by the
    decoded username, need real per-user tokens to prove independence.
    Limits used below are the app's real configured defaults: they're
    captured into the route at import time (see app/core/rate_limit.py),
    so a fixture-level settings override wouldn't reach them.
    """
    db_url = f"sqlite:///{tmp_path}/test.db"
    repo = SQLiteDocumentRepository(db_url)
    Base.metadata.create_all(repo.engine)

    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_llm_provider] = lambda: FakeLLMProvider(response="ok")

    yield TestClient(app)

    app.dependency_overrides.clear()


def _headers(username: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(username)}"}


def test_rate_limit_returns_429(client):
    """7. Exceeding the configured limit returns 429 with Retry-After."""
    headers = _headers("rate_limit_test_user")
    limit = 5  # POST /documents default (RATE_LIMIT_DOCUMENTS_POST)

    for i in range(limit):
        r = client.post(
            "/documents", json={"name": f"doc{i}", "text": "hello world"}, headers=headers
        )
        assert r.status_code == 200

    over_limit = client.post(
        "/documents", json={"name": "one_too_many", "text": "hello world"}, headers=headers
    )
    assert over_limit.status_code == 429
    assert "Retry-After" in over_limit.headers


def test_different_users_limited_independently(client):
    """8. Different authenticated identities have independent counters."""
    limit = 5
    headers_a = _headers("user_a")
    headers_b = _headers("user_b")

    for i in range(limit):
        assert client.post(
            "/documents", json={"name": f"a{i}", "text": "hello"}, headers=headers_a
        ).status_code == 200

    # user_a is now over their own limit
    assert client.post(
        "/documents", json={"name": "a_extra", "text": "hello"}, headers=headers_a
    ).status_code == 429

    # user_b has an independent counter, never touched, not blocked
    assert client.post(
        "/documents", json={"name": "b1", "text": "hello"}, headers=headers_b
    ).status_code == 200


def test_failed_auth_attempts_are_rate_limited(client):
    """Failed logins count toward the /auth/token limit too (task requirement)."""
    limit = 5  # POST /auth/token default (RATE_LIMIT_AUTH_TOKEN)

    for _ in range(limit):
        assert client.post(
            "/auth/token", json={"username": "x", "password": "wrong"}
        ).status_code == 401

    over_limit = client.post("/auth/token", json={"username": "x", "password": "wrong"})
    assert over_limit.status_code == 429