from types import SimpleNamespace

import pytest

from app.agent import checkpointer as checkpointer_module


@pytest.mark.anyio
async def test_checkpointer_uses_postgres_when_connection_is_available(monkeypatch):
    calls: dict[str, object] = {}

    class _FakePostgresSaver:
        def __init__(self, conn):
            calls["conn"] = conn

        async def setup(self):
            calls["setup"] = True

    async def _fake_connect(dsn, **_kwargs):
        calls["dsn"] = dsn
        return object()

    def _fake_settings():
        return SimpleNamespace(
            normalized_database_url="postgres://postgres:postgres@localhost:5432/postgres",
            database_host="localhost",
        )

    monkeypatch.setattr(checkpointer_module, "AsyncPostgresSaver", _FakePostgresSaver)
    monkeypatch.setattr(checkpointer_module.AsyncConnection, "connect", _fake_connect)
    monkeypatch.setattr(checkpointer_module, "get_settings", _fake_settings)
    checkpointer_module._saver = None
    checkpointer_module._conn = None

    saver = await checkpointer_module.get_checkpointer()

    assert isinstance(saver, _FakePostgresSaver)
    assert calls["setup"] is True
    assert calls["dsn"] == "postgres://postgres:postgres@localhost:5432/postgres"


@pytest.mark.anyio
async def test_checkpointer_fails_loudly_on_connection_error(monkeypatch):
    async def _failing_connect(_dsn, **_kwargs):
        raise RuntimeError("cannot connect")

    def _fake_settings():
        return SimpleNamespace(
            normalized_database_url="postgres://postgres:postgres@localhost:5432/postgres",
            database_host="localhost",
        )

    monkeypatch.setattr(checkpointer_module.AsyncConnection, "connect", _failing_connect)
    monkeypatch.setattr(checkpointer_module, "get_settings", _fake_settings)
    checkpointer_module._saver = None
    checkpointer_module._conn = None

    with pytest.raises(RuntimeError, match="Postgres checkpointer unavailable"):
        await checkpointer_module.get_checkpointer()
