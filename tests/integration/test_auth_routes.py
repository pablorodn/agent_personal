from types import SimpleNamespace

from fastapi.testclient import TestClient
from supabase_auth.errors import AuthApiError

from app.dependencies import get_current_user_id, get_db
from app.main import app
from app.routers import auth as auth_router


def test_login_page_renders():
    client = TestClient(app)
    response = client.get("/login")
    assert response.status_code == 200
    assert "Iniciar sesión" in response.text


def test_signup_page_renders():
    client = TestClient(app)
    response = client.get("/signup")
    assert response.status_code == 200
    assert "Crear cuenta" in response.text


def test_signup_existing_user_returns_form_error_not_500():
    class _FakeAuth:
        async def sign_up(self, _payload):
            raise AuthApiError("User already registered", 422, None)

    class _FakeDB:
        auth = _FakeAuth()

    async def _fake_db():
        return _FakeDB()

    app.dependency_overrides[auth_router._db] = _fake_db
    client = TestClient(app)
    response = client.post(
        "/signup",
        data={"email": "existing@example.com", "password": "123456"},
    )
    assert response.status_code == 200
    assert "ya está registrado" in response.text
    app.dependency_overrides.clear()


def test_signup_happy_path_keeps_hx_redirect():
    class _FakeSession:
        access_token = "access-token"
        refresh_token = "refresh-token"

    class _FakeResult:
        user = object()
        session = _FakeSession()

    class _FakeAuth:
        async def sign_up(self, _payload):
            return _FakeResult()

    class _FakeDB:
        auth = _FakeAuth()

    async def _fake_db():
        return _FakeDB()

    app.dependency_overrides[auth_router._db] = _fake_db
    client = TestClient(app)
    response = client.post(
        "/signup",
        data={"email": "new@example.com", "password": "123456"},
    )
    assert response.status_code == 200
    assert response.headers["hx-redirect"] == "/onboarding"
    assert "sb-access-token=" in response.headers.get("set-cookie", "")
    app.dependency_overrides.clear()


def test_auth_callback_redirects_as_page_navigation():
    client = TestClient(app)
    response = client.get("/auth/callback", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_index_redirects_to_onboarding_when_incomplete(
    monkeypatch, patch_auth_middleware, auth_cookie
):
    async def _fake_db():
        return object()

    async def _fake_user_id():
        return "user-1"

    async def _fake_get_profile(_db, _user_id):
        return SimpleNamespace(onboarding_completed=False)

    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[get_current_user_id] = _fake_user_id
    monkeypatch.setattr("app.pages.index.get_profile", _fake_get_profile)
    client = TestClient(app)
    response = client.get("/", cookies=auth_cookie, follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/onboarding"
    app.dependency_overrides.clear()


def test_index_redirects_to_chat_when_completed(
    monkeypatch, patch_auth_middleware, auth_cookie
):
    async def _fake_db():
        return object()

    async def _fake_user_id():
        return "user-1"

    async def _fake_get_profile(_db, _user_id):
        return SimpleNamespace(onboarding_completed=True)

    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[get_current_user_id] = _fake_user_id
    monkeypatch.setattr("app.pages.index.get_profile", _fake_get_profile)
    client = TestClient(app)
    response = client.get("/", cookies=auth_cookie, follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/chat"
    app.dependency_overrides.clear()


def test_auth_middleware_refreshes_expired_access_token_and_continues_request(monkeypatch):
    class _FakeUser:
        def model_dump(self):
            return {"id": "user-1"}

    class _RefreshSession:
        access_token = "new-access-token"
        refresh_token = "new-refresh-token"

    class _RefreshResult:
        user = _FakeUser()
        session = _RefreshSession()

    class _FakeAuth:
        async def get_user(self, token: str):
            if token == "expired-access-token":
                raise RuntimeError("JWT expired")

            class _Response:
                user = _FakeUser()

            return _Response()

        async def refresh_session(self, refresh_token: str):
            assert refresh_token == "valid-refresh-token"
            return _RefreshResult()

    class _FakeClient:
        auth = _FakeAuth()

    async def _fake_create_server_client():
        return _FakeClient()

    async def _fake_db():
        return object()

    async def _fake_user_id():
        return "user-1"

    async def _fake_get_profile(_db, _user_id):
        return SimpleNamespace(onboarding_completed=False)

    monkeypatch.setattr("app.middleware.auth.create_server_client", _fake_create_server_client)
    monkeypatch.setattr("app.pages.index.get_profile", _fake_get_profile)
    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[get_current_user_id] = _fake_user_id

    client = TestClient(app)
    response = client.get(
        "/",
        cookies={
            "sb-access-token": "expired-access-token",
            "sb-refresh-token": "valid-refresh-token",
        },
        follow_redirects=False,
    )
    assert response.status_code == 307
    assert response.headers["location"] == "/onboarding"
    set_cookie = response.headers.get("set-cookie", "")
    assert "sb-access-token=new-access-token" in set_cookie
    assert "sb-refresh-token=new-refresh-token" in set_cookie
    app.dependency_overrides.clear()


def test_auth_middleware_does_not_mask_downstream_errors_as_login_redirect(
    monkeypatch, patch_auth_middleware, auth_cookie
):
    async def _fake_db():
        return object()

    async def _fake_user_id():
        return "user-1"

    async def _boom_profile(_db, _user_id):
        raise RuntimeError("downstream failure")

    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[get_current_user_id] = _fake_user_id
    monkeypatch.setattr("app.pages.index.get_profile", _boom_profile)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/", cookies=auth_cookie, follow_redirects=False)
    assert response.status_code == 500
    assert response.headers.get("location") != "/login"
    app.dependency_overrides.clear()
