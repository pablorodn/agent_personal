import pytest
from langchain_core.messages import HumanMessage

from app.agent.nodes.memory_injection_node import _format_memory_block, memory_injection_node
from app.db.queries import memories as memories_module


@pytest.mark.anyio
async def test_memory_injection_with_existing_memories(monkeypatch):
    calls: dict[str, object] = {}

    async def _fake_embedding(_text: str):
        return [0.1, 0.2]

    async def _fake_match_memories(_db, user_id, query_embedding, limit=8):
        calls["match"] = {"user_id": user_id, "query_embedding": query_embedding, "limit": limit}
        return [
            {"id": "mem-1", "content": "Prefiere respuestas en español", "type": "episodic"},
            {"id": "mem-2", "content": "Le gusta respuestas breves", "type": "episodic"},
        ]

    async def _fake_increment(_db, memory_ids):
        calls["increment"] = memory_ids

    monkeypatch.setattr("app.agent.nodes.memory_injection_node.generate_embedding", _fake_embedding)
    monkeypatch.setattr("app.agent.nodes.memory_injection_node.match_memories", _fake_match_memories)
    monkeypatch.setattr(
        "app.agent.nodes.memory_injection_node.increment_memory_retrieval_count",
        _fake_increment,
    )

    state = {
        "messages": [HumanMessage(content="¿Qué recuerdas de mí?")],
        "system_prompt": "Eres un asistente útil.",
        "user_id": "user-1",
        "session_id": "session-1",
    }
    config = {"configurable": {"tool_ctx": {"db": object(), "user_id": "user-1"}}}

    result = await memory_injection_node(state, config)

    assert "[MEMORIA DEL USUARIO]" in result["system_prompt"]
    assert "Prefiere respuestas en español" in result["system_prompt"]
    assert "Le gusta respuestas breves" in result["system_prompt"]
    assert result["system_prompt"].endswith("Eres un asistente útil.")
    assert calls["match"] == {"user_id": "user-1", "query_embedding": [0.1, 0.2], "limit": 8}
    assert calls["increment"] == ["mem-1", "mem-2"]


@pytest.mark.anyio
async def test_memory_injection_without_memories(monkeypatch):
    calls: dict[str, object] = {}

    async def _fake_embedding(_text: str):
        return [0.5]

    async def _fake_match_memories(_db, _user_id, _query_embedding, limit=8):
        calls["limit"] = limit
        return []

    async def _fake_increment(_db, memory_ids):
        calls["increment"] = memory_ids

    monkeypatch.setattr("app.agent.nodes.memory_injection_node.generate_embedding", _fake_embedding)
    monkeypatch.setattr("app.agent.nodes.memory_injection_node.match_memories", _fake_match_memories)
    monkeypatch.setattr(
        "app.agent.nodes.memory_injection_node.increment_memory_retrieval_count",
        _fake_increment,
    )

    state = {
        "messages": [HumanMessage(content="hola")],
        "system_prompt": "Prompt base",
        "user_id": "user-1",
        "session_id": "session-1",
    }
    config = {"configurable": {"tool_ctx": {"db": object(), "user_id": "user-1"}}}

    result = await memory_injection_node(state, config)

    assert result["system_prompt"] == "Prompt base"
    assert calls["limit"] == 8
    assert "increment" not in calls


@pytest.mark.anyio
async def test_match_memories_uses_match_user_id_rpc_parameter():
    captured: dict[str, object] = {}

    class _FakeResult:
        data = [{"id": "mem-1", "content": "dato"}]

    class _FakeRpc:
        def __init__(self, name, payload):
            captured["name"] = name
            captured["payload"] = payload

        async def execute(self):
            return _FakeResult()

    class _FakeDb:
        def rpc(self, name, payload):
            return _FakeRpc(name, payload)

    result = await memories_module.match_memories(_FakeDb(), "user-1", [0.1, 0.2], limit=8)

    assert captured["name"] == "match_memories"
    assert captured["payload"] == {
        "query_embedding": [0.1, 0.2],
        "match_user_id": "user-1",
        "match_count": 8,
    }
    assert result == [{"id": "mem-1", "content": "dato"}]


def test_format_memory_block_separates_sections_by_type():
    memories = [
        {"id": "mem-1", "content": "Prefiere respuestas en español", "type": "episodic"},
        {"id": "mem-2", "content": "Se llama Pablo y es ingeniero", "type": "semantic"},
    ]

    block = _format_memory_block(memories)

    assert "[HECHOS Y PREFERENCIAS DEL USUARIO]" in block
    assert "[MEMORIA DEL USUARIO]" in block
    assert block.index("[HECHOS Y PREFERENCIAS DEL USUARIO]") < block.index("Se llama Pablo y es ingeniero")
    assert block.index("[MEMORIA DEL USUARIO]") < block.index("Prefiere respuestas en español")


def test_format_memory_block_omits_empty_semantic_section():
    memories = [{"id": "mem-1", "content": "Hoy hablamos de viajes", "type": "episodic"}]

    block = _format_memory_block(memories)

    assert "[HECHOS Y PREFERENCIAS DEL USUARIO]" not in block
    assert "[MEMORIA DEL USUARIO]" in block


def test_format_memory_block_omits_empty_episodic_section():
    memories = [{"id": "mem-1", "content": "Se llama Pablo", "type": "semantic"}]

    block = _format_memory_block(memories)

    assert "[MEMORIA DEL USUARIO]" not in block
    assert "[HECHOS Y PREFERENCIAS DEL USUARIO]" in block
