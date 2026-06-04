from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.agent.graph import AgentOutput
from app.config import get_settings
from app.dependencies import get_db
from app.main import app


def test_telegram_webhook_ok():
    client = TestClient(app)
    settings = get_settings()
    headers = {}
    if settings.telegram_webhook_secret:
        headers["X-Telegram-Bot-Api-Secret-Token"] = settings.telegram_webhook_secret
    response = client.post("/api/telegram/webhook", json={"update_id": 1}, headers=headers)
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_telegram_link_code_links_account(monkeypatch):
    events: dict[str, object] = {}
    settings = get_settings()
    headers = {}
    if settings.telegram_webhook_secret:
        headers["X-Telegram-Bot-Api-Secret-Token"] = settings.telegram_webhook_secret

    async def _fake_db():
        return object()

    async def _fake_get_link_code(_db, _code):
        return {
            "id": "code-1",
            "user_id": "user-1",
            "used": False,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
        }

    async def _fake_link_account(_db, user_id, telegram_user_id, chat_id):
        events["link"] = (user_id, telegram_user_id, chat_id)

    async def _fake_mark_used(_db, link_code_id):
        events["used"] = link_code_id

    async def _fake_send(_chat_id, text, reply_markup=None):
        events["send"] = {"text": text, "reply_markup": reply_markup}
        return {"ok": True}

    app.dependency_overrides[get_db] = _fake_db
    monkeypatch.setattr("app.routers.telegram.get_link_code", _fake_get_link_code)
    monkeypatch.setattr("app.routers.telegram.link_telegram_account", _fake_link_account)
    monkeypatch.setattr("app.routers.telegram.mark_link_code_used", _fake_mark_used)
    monkeypatch.setattr("app.routers.telegram.send_text_message", _fake_send)

    client = TestClient(app)
    response = client.post(
        "/api/telegram/webhook",
        json={
            "update_id": 1,
            "message": {
                "chat": {"id": 111},
                "from": {"id": 222},
                "text": "/link abcd1234",
            },
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert events["link"] == ("user-1", "222", "111")
    assert events["used"] == "code-1"
    assert "vinculada correctamente" in events["send"]["text"]
    app.dependency_overrides.clear()


def test_telegram_link_rejects_used_code(monkeypatch):
    events: dict[str, object] = {}
    settings = get_settings()
    headers = {}
    if settings.telegram_webhook_secret:
        headers["X-Telegram-Bot-Api-Secret-Token"] = settings.telegram_webhook_secret

    async def _fake_db():
        return object()

    async def _fake_get_link_code(_db, _code):
        return {
            "id": "code-1",
            "user_id": "user-1",
            "used": True,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
        }

    async def _fake_send(_chat_id, text, reply_markup=None):
        events["send"] = {"text": text, "reply_markup": reply_markup}
        return {"ok": True}

    async def _fake_link_account(_db, user_id, telegram_user_id, chat_id):
        _ = (user_id, telegram_user_id, chat_id)
        events["linked"] = True

    app.dependency_overrides[get_db] = _fake_db
    monkeypatch.setattr("app.routers.telegram.get_link_code", _fake_get_link_code)
    monkeypatch.setattr("app.routers.telegram.send_text_message", _fake_send)
    monkeypatch.setattr("app.routers.telegram.link_telegram_account", _fake_link_account)

    client = TestClient(app)
    response = client.post(
        "/api/telegram/webhook",
        json={
            "update_id": 10,
            "message": {"chat": {"id": 111}, "from": {"id": 222}, "text": "/link code"},
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert "ya fue utilizado" in events["send"]["text"]
    assert "linked" not in events
    app.dependency_overrides.clear()


def test_telegram_link_rejects_expired_code(monkeypatch):
    events: dict[str, object] = {}
    settings = get_settings()
    headers = {}
    if settings.telegram_webhook_secret:
        headers["X-Telegram-Bot-Api-Secret-Token"] = settings.telegram_webhook_secret

    async def _fake_db():
        return object()

    async def _fake_get_link_code(_db, _code):
        return {
            "id": "code-1",
            "user_id": "user-1",
            "used": False,
            "expires_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
        }

    async def _fake_send(_chat_id, text, reply_markup=None):
        events["send"] = {"text": text, "reply_markup": reply_markup}
        return {"ok": True}

    app.dependency_overrides[get_db] = _fake_db
    monkeypatch.setattr("app.routers.telegram.get_link_code", _fake_get_link_code)
    monkeypatch.setattr("app.routers.telegram.send_text_message", _fake_send)

    client = TestClient(app)
    response = client.post(
        "/api/telegram/webhook",
        json={
            "update_id": 11,
            "message": {"chat": {"id": 111}, "from": {"id": 222}, "text": "/link code"},
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert "Código expirado" in events["send"]["text"]
    app.dependency_overrides.clear()


def test_telegram_message_invokes_run_agent(monkeypatch):
    calls: dict[str, object] = {}
    settings = get_settings()
    headers = {}
    if settings.telegram_webhook_secret:
        headers["X-Telegram-Bot-Api-Secret-Token"] = settings.telegram_webhook_secret

    async def _fake_db():
        return object()

    async def _fake_account(_db, _telegram_user_id):
        return {"user_id": "user-1"}

    async def _fake_session(_db, user_id=None, channel=None):
        _ = user_id
        assert channel == "telegram"
        return SimpleNamespace(id="session-1")

    async def _fake_touch(_db, session_id):
        calls["touch"] = session_id

    async def _fake_add_message(_db, session_id, role, content, structured_payload=None):
        calls.setdefault("messages", []).append((session_id, role, content, structured_payload))
        return SimpleNamespace(id="msg-1")

    async def _fake_profile(_db, _user_id):
        return SimpleNamespace(agent_system_prompt="Sistema")

    async def _fake_tools(_db, _user_id):
        return ["read_file"]

    async def _fake_integration(_db, _user_id, _provider):
        return None

    async def _fake_send(_chat_id, text, reply_markup=None):
        calls["send"] = {"text": text, "reply_markup": reply_markup}
        return {"ok": True}

    async def _fake_run_agent(agent_input):
        calls["run_agent"] = agent_input
        return AgentOutput(response="respuesta telegram", tool_calls=[])

    app.dependency_overrides[get_db] = _fake_db
    monkeypatch.setattr("app.routers.telegram.get_telegram_account_by_telegram_user_id", _fake_account)
    monkeypatch.setattr("app.routers.telegram.get_or_create_active_session", _fake_session)
    monkeypatch.setattr("app.routers.telegram.touch_session", _fake_touch)
    monkeypatch.setattr("app.routers.telegram.add_message", _fake_add_message)
    monkeypatch.setattr("app.routers.telegram.get_profile", _fake_profile)
    monkeypatch.setattr("app.routers.telegram.list_enabled_tool_ids", _fake_tools)
    monkeypatch.setattr("app.routers.telegram.get_integration", _fake_integration)
    monkeypatch.setattr("app.routers.telegram.send_text_message", _fake_send)
    monkeypatch.setattr("app.routers.telegram.run_agent", _fake_run_agent)

    client = TestClient(app)
    response = client.post(
        "/api/telegram/webhook",
        json={
            "update_id": 2,
            "message": {
                "chat": {"id": 111},
                "from": {"id": 222},
                "text": "hola agente",
            },
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert calls["run_agent"].message == "hola agente"
    assert calls["run_agent"].session_id == "session-1"
    assert calls["send"]["text"] == "respuesta telegram"
    app.dependency_overrides.clear()


def test_telegram_unlinked_user_does_not_invoke_run_agent(monkeypatch):
    calls: dict[str, object] = {}
    settings = get_settings()
    headers = {}
    if settings.telegram_webhook_secret:
        headers["X-Telegram-Bot-Api-Secret-Token"] = settings.telegram_webhook_secret

    async def _fake_db():
        return object()

    async def _fake_account(_db, _telegram_user_id):
        return None

    async def _fake_send(_chat_id, text, reply_markup=None):
        calls["send"] = {"text": text, "reply_markup": reply_markup}
        return {"ok": True}

    async def _fake_run_agent(agent_input):
        calls["run_agent"] = agent_input
        return AgentOutput(response="no debería", tool_calls=[])

    app.dependency_overrides[get_db] = _fake_db
    monkeypatch.setattr("app.routers.telegram.get_telegram_account_by_telegram_user_id", _fake_account)
    monkeypatch.setattr("app.routers.telegram.send_text_message", _fake_send)
    monkeypatch.setattr("app.routers.telegram.run_agent", _fake_run_agent)

    client = TestClient(app)
    response = client.post(
        "/api/telegram/webhook",
        json={
            "update_id": 12,
            "message": {"chat": {"id": 111}, "from": {"id": 222}, "text": "hola"},
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert "Primero vincula tu cuenta" in calls["send"]["text"]
    assert "run_agent" not in calls
    app.dependency_overrides.clear()


def test_telegram_callback_query_resumes_hitl(monkeypatch):
    calls: dict[str, object] = {}
    settings = get_settings()
    headers = {}
    if settings.telegram_webhook_secret:
        headers["X-Telegram-Bot-Api-Secret-Token"] = settings.telegram_webhook_secret

    async def _fake_db():
        return object()

    async def _fake_account(_db, _telegram_user_id):
        return {"user_id": "user-1"}

    async def _fake_answer(_callback_id, text=None):
        calls["answered"] = True
        return {"ok": True}

    async def _fake_pending_tool_call(_db, _tool_call_id):
        return SimpleNamespace(session_id="session-1")

    async def _fake_session_by_id(_db, _session_id):
        return SimpleNamespace(user_id="user-1")

    async def _fake_profile(_db, _user_id):
        return SimpleNamespace(agent_system_prompt="Sistema")

    async def _fake_tools(_db, _user_id):
        return []

    async def _fake_integration(_db, _user_id, _provider):
        return None

    async def _fake_add_message(_db, _session_id, _role, _content, structured_payload=None):
        _ = structured_payload
        return SimpleNamespace(id="msg-1")

    async def _fake_send(_chat_id, text, reply_markup=None):
        calls["send"] = {"text": text, "reply_markup": reply_markup}
        return {"ok": True}

    async def _fake_run_agent(agent_input):
        calls["run_agent"] = agent_input
        return AgentOutput(response="confirmado", tool_calls=[])

    app.dependency_overrides[get_db] = _fake_db
    monkeypatch.setattr("app.routers.telegram.get_telegram_account_by_telegram_user_id", _fake_account)
    monkeypatch.setattr("app.routers.telegram.answer_callback_query", _fake_answer)
    monkeypatch.setattr("app.routers.telegram.get_pending_tool_call", _fake_pending_tool_call)
    monkeypatch.setattr("app.routers.telegram.get_session_by_id", _fake_session_by_id)
    monkeypatch.setattr("app.routers.telegram.get_profile", _fake_profile)
    monkeypatch.setattr("app.routers.telegram.list_enabled_tool_ids", _fake_tools)
    monkeypatch.setattr("app.routers.telegram.get_integration", _fake_integration)
    monkeypatch.setattr("app.routers.telegram.add_message", _fake_add_message)
    monkeypatch.setattr("app.routers.telegram.send_text_message", _fake_send)
    monkeypatch.setattr("app.routers.telegram.run_agent", _fake_run_agent)

    client = TestClient(app)
    response = client.post(
        "/api/telegram/webhook",
        json={
            "update_id": 3,
            "callback_query": {
                "id": "cb-1",
                "data": "confirm_approve:toolcall-1",
                "from": {"id": 222},
                "message": {"chat": {"id": 111}},
            },
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert calls["answered"] is True
    assert calls["run_agent"].resume_decision == "approve"
    assert calls["run_agent"].session_id == "session-1"
    assert calls["send"]["text"] == "confirmado"
    app.dependency_overrides.clear()


def test_telegram_callback_query_rejects_foreign_tool_call(monkeypatch):
    calls: dict[str, object] = {}
    settings = get_settings()
    headers = {}
    if settings.telegram_webhook_secret:
        headers["X-Telegram-Bot-Api-Secret-Token"] = settings.telegram_webhook_secret

    async def _fake_db():
        return object()

    async def _fake_account(_db, _telegram_user_id):
        return {"user_id": "user-1"}

    async def _fake_answer(_callback_id, text=None):
        _ = text
        calls["answered"] = True
        return {"ok": True}

    async def _fake_pending_tool_call(_db, _tool_call_id):
        return SimpleNamespace(session_id="session-foreign")

    async def _fake_session_by_id(_db, _session_id):
        return SimpleNamespace(user_id="user-2")

    async def _fake_send(_chat_id, text, reply_markup=None):
        calls["send"] = {"text": text, "reply_markup": reply_markup}
        return {"ok": True}

    async def _fake_run_agent(agent_input):
        calls["run_agent"] = agent_input
        return AgentOutput(response="no debería", tool_calls=[])

    app.dependency_overrides[get_db] = _fake_db
    monkeypatch.setattr("app.routers.telegram.get_telegram_account_by_telegram_user_id", _fake_account)
    monkeypatch.setattr("app.routers.telegram.answer_callback_query", _fake_answer)
    monkeypatch.setattr("app.routers.telegram.get_pending_tool_call", _fake_pending_tool_call)
    monkeypatch.setattr("app.routers.telegram.get_session_by_id", _fake_session_by_id)
    monkeypatch.setattr("app.routers.telegram.send_text_message", _fake_send)
    monkeypatch.setattr("app.routers.telegram.run_agent", _fake_run_agent)

    client = TestClient(app)
    response = client.post(
        "/api/telegram/webhook",
        json={
            "update_id": 13,
            "callback_query": {
                "id": "cb-2",
                "data": "confirm_approve:toolcall-x",
                "from": {"id": 222},
                "message": {"chat": {"id": 111}},
            },
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert calls["answered"] is True
    assert "No tienes permisos" in calls["send"]["text"]
    assert "run_agent" not in calls
    app.dependency_overrides.clear()
