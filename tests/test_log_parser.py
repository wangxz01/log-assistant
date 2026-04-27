from datetime import datetime

from fastapi import HTTPException
import pytest

from app.core.security import create_access_token, decode_access_token
from app.models.user import User
from app.services.log_service import LogService, parse_log_entries


def test_parse_log_entries_extracts_timestamp_level_and_message() -> None:
    content = "\n".join(
        [
            "2026-04-28 10:00:00 INFO service started",
            "2026-04-28T10:01:00Z WARN disk usage high",
            "2026-04-28T10:02:00+00:00 ERROR failed to connect to database",
        ]
    )

    entries = parse_log_entries(content)

    assert len(entries) == 3
    assert entries[0]["timestamp_text"] == "2026-04-28 10:00:00"
    assert entries[0]["level"] == "INFO"
    assert entries[0]["is_key_event"] is False
    assert entries[1]["level"] == "WARN"
    assert entries[1]["is_key_event"] is True
    assert entries[2]["level"] == "ERROR"
    assert entries[2]["is_key_event"] is True


def test_access_token_can_be_decoded() -> None:
    token = create_access_token(subject="1", extra_claims={"email": "student@example.com"})

    payload = decode_access_token(token)

    assert payload is not None
    assert payload["sub"] == "1"
    assert payload["email"] == "student@example.com"


def test_other_user_cannot_access_log_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    service = LogService()
    owner = User(id=1, email="owner@example.com", password_hash="hash")
    other_user = User(id=2, email="other@example.com", password_hash="hash")

    def fake_get_log_row(log_id: int, user: User) -> dict[str, object]:
        if log_id == 1 and user.id == owner.id:
            return {
                "id": 1,
                "original_filename": "owner.log",
                "status": "parsed",
                "owner_email": owner.email,
                "uploaded_at": datetime(2026, 4, 28, 10, 0, 0),
                "size_bytes": 128,
                "storage_path": "/tmp/owner.log",
            }

        raise HTTPException(status_code=404, detail="Log not found.")

    monkeypatch.setattr("app.services.log_service.initialize_database", lambda: None)
    monkeypatch.setattr(service, "_get_log_row", fake_get_log_row)

    with pytest.raises(HTTPException) as exc_info:
        service.get_log(1, other_user)

    assert exc_info.value.status_code == 404


def test_other_user_cannot_analyze_log(monkeypatch: pytest.MonkeyPatch) -> None:
    service = LogService()
    other_user = User(id=2, email="other@example.com", password_hash="hash")

    def fake_get_log_row(log_id: int, user: User) -> dict[str, object]:
        raise HTTPException(status_code=404, detail="Log not found.")

    monkeypatch.setattr("app.services.log_service.initialize_database", lambda: None)
    monkeypatch.setattr(service, "_get_log_row", fake_get_log_row)

    with pytest.raises(HTTPException) as exc_info:
        service.analyze(1, other_user)

    assert exc_info.value.status_code == 404
