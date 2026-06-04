from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.dependencies import get_current_user_id, get_db
from app.main import app


def test_settings_get_loads_real_data(monkeypatch, patch_auth_middleware, auth_cookie):
    async def _fake_db():
        return object()

    async def _fake_user_id():
        return "user-1"

    async def _fake_get_profile(_db, _user_id):
        return SimpleNamespace(name="Pablo", agent_name="Atlas", agent_system_prompt="Hola")

    async def _fake_enabled_tools(_db, _user_id):
        return ["read_file"]

    async def _fake_get_integration(_db, _user_id, _provider):
        return SimpleNamespace(status="active")

    async def _fake_is_telegram_linked(_db, _user_id):
        return True

    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[get_current_user_id] = _fake_user_id
    monkeypatch.setattr("app.pages.settings.get_profile", _fake_get_profile)
    monkeypatch.setattr("app.pages.settings.list_enabled_tool_ids", _fake_enabled_tools)
    monkeypatch.setattr("app.pages.settings.get_integration", _fake_get_integration)
    monkeypatch.setattr("app.pages.settings.is_telegram_linked", _fake_is_telegram_linked)

    client = TestClient(app)
    response = client.get("/settings", cookies=auth_cookie)
    assert response.status_code == 200
    assert "Atlas" in response.text
    assert "Cuenta de Telegram vinculada." in response.text
    assert 'href="/settings"' in response.text
    assert "bg-blue-50 text-blue-700" in response.text
    app.dependency_overrides.clear()


def test_settings_post_persists_profile_and_tools(
    monkeypatch, patch_auth_middleware, auth_cookie
):
    calls: dict[str, object] = {}

    async def _fake_db():
        return object()

    async def _fake_user_id():
        return "user-1"

    async def _fake_upsert_profile(_db, payload):
        calls["profile"] = payload
        return SimpleNamespace(**payload)

    async def _fake_replace_enabled_tools(_db, user_id, tool_ids):
        calls["tools"] = {"user_id": user_id, "tool_ids": tool_ids}

    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[get_current_user_id] = _fake_user_id
    monkeypatch.setattr("app.pages.settings.upsert_profile", _fake_upsert_profile)
    monkeypatch.setattr("app.pages.settings.replace_enabled_tools", _fake_replace_enabled_tools)

    client = TestClient(app)
    response = client.post(
        "/settings",
        cookies=auth_cookie,
        data={
            "name": "Pablo",
            "agent_name": "Atlas",
            "system_prompt": "Ayuda",
            "enabled_tools": ["read_file", "invalid_tool"],
        },
    )
    assert response.status_code == 200
    assert "Guardado correctamente." in response.text
    assert calls["profile"]["agent_name"] == "Atlas"
    assert calls["tools"] == {"user_id": "user-1", "tool_ids": ["read_file"]}
    app.dependency_overrides.clear()
