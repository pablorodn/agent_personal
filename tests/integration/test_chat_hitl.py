from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.dependencies import get_current_user_id, get_db
from app.main import app
from app.services.hitl import build_confirmation_message, sanitize_args


def test_sanitize_args_redacts_sensitive_fields():
    out = sanitize_args("bash", {"command": "ls", "token": "secret"})
    assert out["token"] == "***"
    assert out["command"] == "ls"


def test_confirmation_message_contains_tool():
    msg = build_confirmation_message("bash", {"command": "pwd"})
    assert "bash" in msg


def test_chat_page_uses_profile_and_pending_state(
    monkeypatch, patch_auth_middleware, auth_cookie
):
    async def _fake_db():
        return object()

    async def _fake_user_id():
        return "user-1"

    async def _fake_list_sessions(_db, user_id: str, channel: str = "web"):
        _ = (user_id, channel)
        return [SimpleNamespace(id="session-1", last_used_at="2026-06-04T10:00:00+00:00")]

    async def _fake_session(_db, user_id: str, channel: str):
        _ = (user_id, channel)
        return SimpleNamespace(id="session-1")

    async def _fake_touch(_db, session_id: str):
        _ = session_id

    async def _fake_messages(_db, session_id: str):
        _ = session_id
        return []

    async def _fake_profile(_db, user_id: str):
        _ = user_id
        return SimpleNamespace(agent_name="Atlas")

    async def _fake_pending(_db, session_id: str):
        _ = session_id
        return True

    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[get_current_user_id] = _fake_user_id
    monkeypatch.setattr("app.pages.chat.get_or_create_active_session", _fake_session)
    monkeypatch.setattr("app.pages.chat.list_sessions", _fake_list_sessions)
    monkeypatch.setattr("app.pages.chat.touch_session", _fake_touch)
    monkeypatch.setattr("app.pages.chat.get_session_messages", _fake_messages)
    monkeypatch.setattr("app.pages.chat.get_profile", _fake_profile)
    monkeypatch.setattr("app.pages.chat.has_pending_confirmation_for_session", _fake_pending)

    client = TestClient(app)
    response = client.get("/chat", cookies=auth_cookie)
    assert response.status_code == 200
    assert "Atlas" in response.text
    assert "Aprueba o cancela la acción pendiente antes de continuar." in response.text
    assert 'href="/chat"' in response.text
    assert "bg-blue-50 text-blue-700" in response.text
    app.dependency_overrides.clear()


def test_chat_refresh_keeps_visible_history(monkeypatch, patch_auth_middleware, auth_cookie):
    async def _fake_db():
        return object()

    async def _fake_user_id():
        return "user-1"

    async def _fake_session(_db, user_id: str, channel: str):
        _ = (user_id, channel)
        return SimpleNamespace(id="session-1")

    async def _fake_sessions(_db, user_id: str, channel: str = "web"):
        _ = (user_id, channel)
        return [SimpleNamespace(id="session-1", last_used_at="2026-06-04T10:00:00+00:00")]

    async def _fake_messages(_db, session_id: str):
        _ = session_id
        return [SimpleNamespace(role="assistant", content="Historial visible", structured_payload=None)]

    async def _fake_profile(_db, user_id: str):
        _ = user_id
        return SimpleNamespace(agent_name="Atlas")

    async def _fake_pending(_db, session_id: str):
        _ = session_id
        return False

    async def _fake_touch(_db, session_id: str):
        _ = session_id
        return None

    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[get_current_user_id] = _fake_user_id
    monkeypatch.setattr("app.pages.chat.get_or_create_active_session", _fake_session)
    monkeypatch.setattr("app.pages.chat.list_sessions", _fake_sessions)
    monkeypatch.setattr("app.pages.chat.get_session_messages", _fake_messages)
    monkeypatch.setattr("app.pages.chat.get_profile", _fake_profile)
    monkeypatch.setattr("app.pages.chat.has_pending_confirmation_for_session", _fake_pending)
    monkeypatch.setattr("app.pages.chat.touch_session", _fake_touch)

    client = TestClient(app)
    first = client.get("/chat", cookies=auth_cookie)
    second = client.get("/chat", cookies=auth_cookie)
    assert first.status_code == 200
    assert second.status_code == 200
    assert "Historial visible" in second.text
    app.dependency_overrides.clear()
