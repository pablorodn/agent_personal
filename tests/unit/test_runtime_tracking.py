import json

import pytest
from langchain_core.messages import AIMessage

from app.agent.graph import (
    MAX_TOOL_ITERATIONS,
    MAX_TOOL_ITERATIONS_LIMIT_MESSAGE,
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
