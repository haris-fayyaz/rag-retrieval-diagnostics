import datetime

import bcrypt
import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token
from app.database.models import Base
from app.database.repositories.sqlite_repository import SQLiteDocumentRepository
from app.llm.fake_provider import FakeLLMProvider
from app.main import app, get_llm_provider, get_repository


@pytest.fixture
def client(tmp_path, monkeypatch):
    """
    Auth is NOT bypassed here (unlike the other test files) - this file
    tests the real flow. monkeypatch sets known credentials directly on
    the settings singleton, since it's already built by the time this
    fixture runs - setting env vars here would be too late.
    """
    monkeypatch.setattr(settings, "app_username", "test_admin")
    monkeypatch.setattr(
        settings,
        "app_password_hash",
        bcrypt.hashpw(b"correct_password", bcrypt.gensalt()).decode(),
    )

    db_url = f"sqlite:///{tmp_path}/test.db"
    repo = SQLiteDocumentRepository(db_url)
    Base.metadata.create_all(repo.engine)

    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_llm_provider] = lambda: FakeLLMProvider(response="ok")

    yield TestClient(app)

    app.dependency_overrides.clear()


def _expired_token() -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {"sub": "test_admin", "iat": now, "exp": now - datetime.timedelta(minutes=1)}
    return pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def test_correct_credentials_return_valid_token(client):
    """1. Token endpoint returns a valid JWT for correct credentials."""
    r = client.post("/auth/token", json={"username": "test_admin", "password": "correct_password"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.jwt_expire_minutes * 60
    assert decode_access_token(body["access_token"]) == "test_admin"


def test_incorrect_credentials_rejected(client):
    """2. Incorrect credentials are rejected."""
    assert client.post(
        "/auth/token", json={"username": "test_admin", "password": "wrong"}
    ).status_code == 401
    assert client.post(
        "/auth/token", json={"username": "nobody", "password": "correct_password"}
    ).status_code == 401


def test_missing_token_returns_401(client):
    """3. Missing token returns 401."""
    assert client.get("/documents").status_code == 401


def test_invalid_and_expired_token_return_401(client):
    """4. Invalid or expired token returns 401."""
    assert client.get(
        "/documents", headers={"Authorization": "Bearer garbage"}
    ).status_code == 401
    assert client.get(
        "/documents", headers={"Authorization": f"Bearer {_expired_token()}"}
    ).status_code == 401


def test_valid_token_allows_access(client):
    """5. Valid token allows access."""
    headers = {"Authorization": f"Bearer {create_access_token('test_admin')}"}
    assert client.get("/documents", headers=headers).status_code == 200


def test_health_remains_public(client):
    """6. /health remains public, with or without a token."""
    assert client.get("/health").status_code == 200
    assert client.get("/health", headers={"Authorization": "Bearer garbage"}).status_code == 200


def test_secrets_and_tokens_not_in_logs_or_errors(client, caplog):
    """11. Passwords and the JWT secret never appear in a response body or a log line."""
    responses = [
        client.post("/auth/token", json={"username": "test_admin", "password": "correct_password"}),
        client.post("/auth/token", json={"username": "test_admin", "password": "wrong_password_xyz"}),
        client.get("/documents", headers={"Authorization": "Bearer not.a.valid.jwt"}),
    ]
    for response in responses:
        assert "correct_password" not in response.text
        assert "wrong_password_xyz" not in response.text
        assert settings.jwt_secret not in response.text

    assert "correct_password" not in caplog.text
    assert "wrong_password_xyz" not in caplog.text
    assert settings.jwt_secret not in caplog.text