import pytest

from app.agent import checkpointer


async def test_get_checkpointer_raises_when_postgres_is_unavailable(monkeypatch):
    class _FailingPool:
        def __init__(self, *_args, **_kwargs):
            pass

        async def open(self):
            raise OSError("dns resolution failed")

    monkeypatch.setattr(checkpointer, "AsyncConnectionPool", _FailingPool)
    checkpointer._saver = None
    checkpointer._pool = None

    with pytest.raises(RuntimeError, match="Postgres checkpointer unavailable"):
        await checkpointer.get_checkpointer()
