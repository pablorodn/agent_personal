import pytest

from app.agent.memory_flush import flush_session_memory
from app.services.memory_policy import can_store_memory


def test_memory_policy_blocks_sensitive_text():
    assert can_store_memory("my token is 123") is False


def test_memory_policy_allows_regular_text():
    assert can_store_memory("I prefer replies in Spanish") is True


@pytest.mark.anyio
async def test_flush_session_memory_handles_external_errors(monkeypatch):
    async def _fake_messages(_db, _session_id):
        return [{"content": "hola"}]

    async def _broken_embedding(_text):
        raise RuntimeError("embedding down")

    monkeypatch.setattr("app.agent.memory_flush.get_session_messages", _fake_messages)
    monkeypatch.setattr("app.agent.memory_flush.generate_embedding", _broken_embedding)

    await flush_session_memory(db=object(), user_id="user-1", session_id="session-1")
