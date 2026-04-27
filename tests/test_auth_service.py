import base64
import json
from typing import Any

import psycopg
import pytest
from fastapi import HTTPException

from app.schemas.auth import LoginRequest, RegisterRequest
from app.services import auth_service as auth_module
from app.services.auth_service import AuthService


class FakeResult:
    def __init__(self, row: dict[str, Any] | None = None) -> None:
        self._row = row

    def fetchone(self) -> dict[str, Any] | None:
        return self._row


class FakeConnection:
    def __init__(self, users: dict[str, dict[str, Any]]) -> None:
        self._users = users

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def execute(self, query: str, params: tuple[str, ...]) -> FakeResult:
        normalized_query = " ".join(query.lower().split())

        if normalized_query.startswith("select"):
            email = params[0]
            return FakeResult(self._users.get(email))

        if normalized_query.startswith("insert"):
            email, password_hash = params

            if email in self._users:
                raise psycopg.errors.UniqueViolation("duplicate email")

            self._users[email] = {
                "id": len(self._users) + 1,
                "email": email,
                "password_hash": password_hash,
            }
            return FakeResult()

        raise AssertionError(f"Unexpected query: {query}")


@pytest.fixture
def fake_users(monkeypatch: pytest.MonkeyPatch) -> dict[str, dict[str, Any]]:
    users: dict[str, dict[str, Any]] = {}
    monkeypatch.setattr(auth_module, "initialize_database", lambda: None)
    monkeypatch.setattr(auth_module, "get_connection", lambda: FakeConnection(users))
    return users


def test_register_creates_user_with_hashed_password(fake_users: dict[str, dict[str, Any]]) -> None:
    service = AuthService()

    response = service.register(RegisterRequest(email="Student@Example.com", password="password123"))

    assert response.message == "User student@example.com registered."
    assert fake_users["student@example.com"]["password_hash"] != "password123"
    assert fake_users["student@example.com"]["password_hash"].startswith("pbkdf2_sha256$")


def test_register_rejects_duplicate_email(fake_users: dict[str, dict[str, Any]]) -> None:
    service = AuthService()
    payload = RegisterRequest(email="student@example.com", password="password123")

    service.register(payload)

    with pytest.raises(HTTPException) as exc_info:
        service.register(payload)

    assert exc_info.value.status_code == 409


def test_login_returns_signed_access_token(fake_users: dict[str, dict[str, Any]]) -> None:
    service = AuthService()
    service.register(RegisterRequest(email="student@example.com", password="password123"))

    response = service.login(LoginRequest(email="student@example.com", password="password123"))

    assert response.token_type == "bearer"
    assert response.access_token.count(".") == 2
    assert "demo-token" not in response.access_token
    assert _decode_jwt_payload(response.access_token)["email"] == "student@example.com"


def test_login_rejects_wrong_password(fake_users: dict[str, dict[str, Any]]) -> None:
    service = AuthService()
    service.register(RegisterRequest(email="student@example.com", password="password123"))

    with pytest.raises(HTTPException) as exc_info:
        service.login(LoginRequest(email="student@example.com", password="wrong-password"))

    assert exc_info.value.status_code == 401


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    payload = token.split(".")[1]
    padding = "=" * (-len(payload) % 4)
    decoded = base64.urlsafe_b64decode(f"{payload}{padding}")
    return json.loads(decoded)
