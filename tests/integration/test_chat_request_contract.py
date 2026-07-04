from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.dependencies import get_current_user_id, get_db
from app.main import app


def test_chat_rejects_invalid_payload_with_controlled_html_response(
    monkeypatch, patch_auth_middleware, auth_cookie
):
    async def _fake_db():
        return object()

    async def _fake_user_id():
        return "user-1"

    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[get_current_user_id] = _fake_user_id
    monkeypatch.setattr("app.routers.chat.get_session_by_id", lambda *_args, **_kwargs: None)

    client = TestClient(app)
    response = client.post(
        "/api/chat",
        cookies=auth_cookie,
        data={"message": " ", "session_id": ""},
    )
    assert response.status_code == 400
    assert "No pude procesar el mensaje" in response.text
    app.dependency_overrides.clear()


def test_chat_accepts_valid_payload_without_422(monkeypatch, patch_auth_middleware, auth_cookie):
    async def _fake_db():
        return object()

    async def _fake_user_id():
        return "user-1"

    async def _fake_session(_db, _session_id):
        return SimpleNamespace(id="session-1", user_id="user-1")

    async def _fake_add_message(_db, _session_id, role, content, structured_payload=None):
        _ = structured_payload
        return SimpleNamespace(id="msg-1", role=role, content=content)

    async def _fake_profile(_db, _user_id):
        return SimpleNamespace(
            name="Pablo", language="es", timezone="America/Bogota", agent_system_prompt="Sistema"
        )

    async def _fake_tools(_db, _user_id):
        return ["read_file"]

    async def _fake_run_agent(_input):
        from app.agent.graph import AgentOutput

        return AgentOutput(response="ok", tool_calls=[])

    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[get_current_user_id] = _fake_user_id
    monkeypatch.setattr("app.routers.chat.get_session_by_id", _fake_session)
    monkeypatch.setattr("app.routers.chat.add_message", _fake_add_message)
    monkeypatch.setattr("app.routers.chat.get_profile", _fake_profile)
    monkeypatch.setattr("app.routers.chat.list_enabled_tool_ids", _fake_tools)
    monkeypatch.setattr("app.routers.chat.run_agent", _fake_run_agent)

    client = TestClient(app)
    response = client.post(
        "/api/chat",
        cookies=auth_cookie,
        data={"message": "hola", "session_id": "session-1"},
    )
    assert response.status_code == 200
    assert "ok" in response.text
    app.dependency_overrides.clear()
