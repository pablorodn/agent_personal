import pytest

from app.agent import checkpointer


async def test_get_checkpointer_raises_when_postgres_is_unavailable(monkeypatch):
    async def _boom(_database_url: str, **_kwargs):
        raise OSError("dns resolution failed")

    monkeypatch.setattr(checkpointer.AsyncConnection, "connect", _boom)
    checkpointer._saver = None
    checkpointer._conn = None

    with pytest.raises(RuntimeError, match="Postgres checkpointer unavailable"):
        await checkpointer.get_checkpointer()
