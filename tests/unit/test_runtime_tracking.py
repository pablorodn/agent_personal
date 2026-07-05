import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agent.graph import (
    MAX_TOOL_ITERATIONS,
    MAX_TOOL_ITERATIONS_LIMIT_MESSAGE,
    agent_node,
    limit_reached_node,
    should_continue,
    tool_executor_node,
)
from app.tools.adapters import TOOL_HANDLERS


@pytest.mark.anyio
async def test_low_tool_execution_inserts_tool_call_record(monkeypatch):
    tracking_calls: list[dict[str, object]] = []

    async def _fake_run_with_tracking(**kwargs):
        tracking_calls.append(kwargs)
        return {"preferences": {"language": "es"}}

    async def _fake_handler(_args, _ctx):
        raise AssertionError("handler should run via run_with_tracking")

    monkeypatch.setitem(TOOL_HANDLERS, "get_user_preferences", _fake_handler)
    monkeypatch.setattr("app.agent.graph.run_with_tracking", _fake_run_with_tracking)

    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tc-low-1",
                        "name": "get_user_preferences",
                        "args": {},
                    }
                ],
            )
        ],
        "session_id": "session-1",
        "tool_iteration_count": 0,
        "bypass_confirmation": False,
    }
    config = {
        "configurable": {
            "tool_ctx": {
                "db": object(),
                "user_id": "user-1",
                "session_id": "session-1",
                "enabled_tools": ["get_user_preferences"],
            }
        }
    }

    result = await tool_executor_node(state, config)

    assert len(tracking_calls) == 1
    assert tracking_calls[0]["tool_id"] == "get_user_preferences"
    assert tracking_calls[0]["session_id"] == "session-1"
    assert tracking_calls[0]["model_tool_call_id"] == "tc-low-1"
    assert result["tool_iteration_count"] == 1
    assert len(result["messages"]) == 1
    assert json.loads(result["messages"][0].content) == {"preferences": {"language": "es"}}


def test_should_continue_routes_to_limit_when_max_iterations_exceeded():
    pending_tool_call = AIMessage(
        content="",
        tool_calls=[{"id": "tc-7", "name": "get_user_preferences", "args": {}}],
    )
    state = {
        "messages": [pending_tool_call],
        "tool_iteration_count": MAX_TOOL_ITERATIONS,
    }

    assert should_continue(state) == "limit_reached"


@pytest.mark.anyio
async def test_limit_reached_preserves_unexecuted_tool_calls_and_adds_limit_message():
    pending_tool_call = AIMessage(
        content="",
        tool_calls=[{"id": "tc-7", "name": "get_user_preferences", "args": {}}],
    )
    state = {
        "messages": [pending_tool_call],
        "tool_iteration_count": MAX_TOOL_ITERATIONS,
    }

    result = await limit_reached_node(state)

    assert len(result["messages"]) == 1
    assert result["messages"][0].content == MAX_TOOL_ITERATIONS_LIMIT_MESSAGE
    assert not result["messages"][0].tool_calls
    assert state["messages"][-1] is pending_tool_call
    assert state["messages"][-1].tool_calls[0]["id"] == "tc-7"


@pytest.mark.anyio
async def test_agent_node_binds_real_schema_and_tool_executor_runs_it(monkeypatch):
    """Ejercita el flujo real (no sintetiza tool_calls directo en tool_executor_node):
    agent_node construye el schema desde TOOL_CATALOG/enabled_tools y lo pasa a
    create_chat_model()/bind_tools(); el AIMessage con tool_calls que produce el
    modelo (fake, para no llamar a OpenRouter) es luego ejecutado de verdad por
    tool_executor_node."""
    captured_schemas: list[list[dict] | None] = []

    class _FakeBoundModel:
        async def ainvoke(self, _messages):
            return AIMessage(
                content="",
                tool_calls=[{"id": "tc-real-1", "name": "get_user_preferences", "args": {}}],
            )

    def _fake_create_chat_model(model_name, tool_schemas=None):
        captured_schemas.append(tool_schemas)
        return _FakeBoundModel()

    monkeypatch.setattr("app.agent.model.create_chat_model", _fake_create_chat_model)

    config = {
        "configurable": {
            "tool_ctx": {
                "db": object(),
                "user_id": "user-1",
                "session_id": "session-1",
                "enabled_tools": ["get_user_preferences"],
            }
        }
    }
    agent_state = {
        "messages": [HumanMessage(content="¿Cuáles son mis preferencias guardadas?")],
        "system_prompt": "Eres un asistente útil.",
    }

    agent_result = await agent_node(agent_state, config)

    assert captured_schemas[0] is not None
    schema_names = {schema["function"]["name"] for schema in captured_schemas[0]}
    assert schema_names == {"get_user_preferences"}

    ai_message = agent_result["messages"][0]
    assert ai_message.tool_calls
    assert ai_message.tool_calls[0]["name"] == "get_user_preferences"

    async def _fake_run_with_tracking(**kwargs):
        return {"preferences": {"language": "es"}}

    monkeypatch.setattr("app.agent.graph.run_with_tracking", _fake_run_with_tracking)

    tool_state = {
        "messages": [*agent_state["messages"], ai_message],
        "session_id": "session-1",
        "tool_iteration_count": 0,
        "bypass_confirmation": False,
    }
    tool_result = await tool_executor_node(tool_state, config)

    assert len(tool_result["messages"]) == 1
    assert json.loads(tool_result["messages"][0].content) == {"preferences": {"language": "es"}}


@pytest.mark.anyio
async def test_tool_executor_node_fails_closed_when_no_tools_enabled():
    """Con enabled_tools vacío/no seteado, ninguna tool ejecuta aunque el modelo
    "intente" llamarla -- confirma el fix de fail-open a fail-closed."""
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[{"id": "tc-blocked-1", "name": "get_user_preferences", "args": {}}],
            )
        ],
        "session_id": "session-1",
        "tool_iteration_count": 0,
        "bypass_confirmation": False,
    }
    config = {
        "configurable": {
            "tool_ctx": {
                "db": object(),
                "user_id": "user-1",
                "session_id": "session-1",
                "enabled_tools": [],
            }
        }
    }

    result = await tool_executor_node(state, config)

    assert len(result["messages"]) == 1
    assert json.loads(result["messages"][0].content) == {
        "error": "Tool not enabled: get_user_preferences"
    }
