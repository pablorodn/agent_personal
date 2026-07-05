from types import SimpleNamespace

import pytest

from app.agent.memory_flush import flush_session_memory


def _msg(role, content):
    return SimpleNamespace(role=role, content=content)


@pytest.mark.anyio
async def test_flush_session_memory_uses_classified_type(monkeypatch):
    messages = [_msg("user", "Me gusta el mate y trabajo como ingeniero")]
    calls: dict[str, object] = {}

    async def _fake_get_session_messages(_db, _session_id):
        return messages

    async def _fake_generate_embedding(_text):
        return [0.1, 0.2]

    async def _fake_classify_memory_type(_content):
        return "semantic"

    async def _fake_save_memory(_db, *, user_id, memory_type, content, embedding):
        calls["save"] = {
            "user_id": user_id,
            "memory_type": memory_type,
            "content": content,
            "embedding": embedding,
        }

    monkeypatch.setattr("app.agent.memory_flush.get_session_messages", _fake_get_session_messages)
    monkeypatch.setattr("app.agent.memory_flush.can_store_memory", lambda _content: True)
    monkeypatch.setattr("app.agent.memory_flush.classify_memory_type", _fake_classify_memory_type)
    monkeypatch.setattr("app.agent.memory_flush.generate_embedding", _fake_generate_embedding)
    monkeypatch.setattr("app.agent.memory_flush.save_memory", _fake_save_memory)

    await flush_session_memory(db=object(), user_id="user-1", session_id="session-1")

    assert calls["save"]["memory_type"] == "semantic"
    assert calls["save"]["content"] == "Me gusta el mate y trabajo como ingeniero"


@pytest.mark.anyio
async def test_flush_session_memory_skips_classification_when_privacy_filtered(monkeypatch):
    messages = [_msg("user", "contenido sensible")]
    called = {"classify": False, "save": False}

    async def _fake_get_session_messages(_db, _session_id):
        return messages

    async def _fake_classify_memory_type(_content):
        called["classify"] = True
        return "semantic"

    async def _fake_save_memory(*_args, **_kwargs):
        called["save"] = True

    monkeypatch.setattr("app.agent.memory_flush.get_session_messages", _fake_get_session_messages)
    monkeypatch.setattr("app.agent.memory_flush.can_store_memory", lambda _content: False)
    monkeypatch.setattr("app.agent.memory_flush.classify_memory_type", _fake_classify_memory_type)
    monkeypatch.setattr("app.agent.memory_flush.save_memory", _fake_save_memory)

    await flush_session_memory(db=object(), user_id="user-1", session_id="session-1")

    assert called["classify"] is False
    assert called["save"] is False
