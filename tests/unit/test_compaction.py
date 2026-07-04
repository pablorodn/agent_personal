import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agent import compaction as compaction_module
from app.agent.compaction import (
    CIRCUIT_BREAKER_LIMIT,
    COMPACTION_TAIL_SIZE,
    llm_compact,
    microcompact,
    should_compact,
)
from app.agent.nodes.compaction_node import compaction_node


def test_should_compact_respects_threshold():
    short = [HumanMessage(content="hola")]
    assert should_compact(short) is False

    big_chars = int(
        compaction_module.CONTEXT_WINDOW_TOKENS
        * compaction_module.COMPACTION_THRESHOLD
        * compaction_module.CHARS_PER_TOKEN
    )
    long_context = [HumanMessage(content="x" * big_chars)]
    assert should_compact(long_context) is True


def test_microcompact_preserves_recent_tail():
    messages = [HumanMessage(content=f"msg-{index}") for index in range(15)]
    compacted = microcompact(messages)

    assert len(compacted) == COMPACTION_TAIL_SIZE
    assert compacted[0].content == "msg-5"
    assert compacted[-1].content == "msg-14"


@pytest.mark.anyio
async def test_llm_compact_preserves_recent_tail(monkeypatch):
    messages = [HumanMessage(content=f"msg-{index}") for index in range(15)]
    llm_calls: list[str] = []

    class _FakeModel:
        async def ainvoke(self, prompt_messages):
            llm_calls.append(str(prompt_messages[0].content))
            return AIMessage(content="## Contexto\nresumen\n## Acciones y herramientas\nninguna")

    monkeypatch.setattr(
        "app.agent.compaction.create_compaction_model",
        lambda: _FakeModel(),
    )

    result = await llm_compact(messages)

    assert len(result) == COMPACTION_TAIL_SIZE + 1
    assert isinstance(result[0], SystemMessage)
    assert "[RESUMEN DE CONTEXTO COMPACTADO]" in str(result[0].content)
    assert "## Contexto" in str(result[0].content)
    assert result[1].content == "msg-5"
    assert result[-1].content == "msg-14"
    assert any("## Contexto" in call for call in llm_calls)


@pytest.mark.anyio
async def test_compaction_node_circuit_breaker_skips_llm_after_limit(monkeypatch):
    messages = [HumanMessage(content=f"msg-{index}") for index in range(15)]
    llm_calls = 0

    async def _fail_llm(_messages):
        nonlocal llm_calls
        llm_calls += 1
        raise RuntimeError("llm unavailable")

    monkeypatch.setattr("app.agent.nodes.compaction_node.should_compact", lambda _messages: True)
    monkeypatch.setattr("app.agent.nodes.compaction_node.llm_compact", _fail_llm)

    state = {
        "messages": messages,
        "compaction_count": 0,
        "compaction_failure_count": CIRCUIT_BREAKER_LIMIT,
        "session_id": "session-1",
    }

    result = await compaction_node(state)

    assert llm_calls == 0
    assert result["compaction_failure_count"] == CIRCUIT_BREAKER_LIMIT
    assert len(result["messages"]) == COMPACTION_TAIL_SIZE + 1
    assert result["messages"][1].content == "msg-5"
    assert result["messages"][-1].content == "msg-14"


@pytest.mark.anyio
async def test_compaction_node_increments_failure_count_before_breaker(monkeypatch):
    messages = [HumanMessage(content=f"msg-{index}") for index in range(15)]
    llm_calls = 0

    async def _fail_llm(_messages):
        nonlocal llm_calls
        llm_calls += 1
        raise RuntimeError("llm unavailable")

    monkeypatch.setattr("app.agent.nodes.compaction_node.should_compact", lambda _messages: True)
    monkeypatch.setattr("app.agent.nodes.compaction_node.llm_compact", _fail_llm)

    state = {
        "messages": messages,
        "compaction_count": 0,
        "compaction_failure_count": 0,
        "session_id": "session-1",
    }

    result = await compaction_node(state)

    assert llm_calls == 1
    assert result["compaction_failure_count"] == 1
    assert result["messages"][-1].content == "msg-14"
