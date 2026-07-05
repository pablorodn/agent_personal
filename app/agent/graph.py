import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from supabase import AsyncClient

from app.agent.checkpointer import get_checkpointer
from app.agent.langfuse import augment_invoke_config
from app.agent.model import ainvoke_chat_with_fallback
from app.agent.nodes.compaction_node import compaction_node
from app.agent.nodes.memory_injection_node import memory_injection_node
from app.agent.state import AgentState
from app.db.queries.tool_calls import find_or_create_pending_tool_call, update_tool_call_status
from app.services.hitl import build_confirmation_message, sanitize_args
from app.tools.adapters import TOOL_HANDLERS
from app.tools.catalog import get_tool_risk, tool_requires_confirmation
from app.tools.with_tracking import run_with_tracking

MAX_TOOL_ITERATIONS = 6
MAX_TOOL_ITERATIONS_LIMIT_MESSAGE = (
    "Alcancé el límite de 6 iteraciones de herramientas para este turno. "
    "Respondo con lo obtenido hasta ahora; si necesitás más pasos, enviá otro mensaje."
)


@dataclass
class AgentInput:
    user_id: str
    session_id: str
    system_prompt: str
    db: AsyncClient
    enabled_tools: list[str]
    message: str | None = None
    resume_decision: str | None = None
    bypass_confirmation: bool = False
    attachment_blocks: list[dict[str, Any]] | None = None


@dataclass
class PendingConfirmation:
    tool_call_id: str
    model_tool_call_id: str
    tool_name: str
    risk: str
    message: str
    args_preview: dict[str, Any]
    session_id: str


@dataclass
class AgentOutput:
    response: str
    tool_calls: list[str]
    pending_confirmation: PendingConfirmation | None = None


def parse_pending_confirmation(final_state: dict[str, Any]) -> PendingConfirmation | None:
    interrupts = final_state.get("__interrupt__", [])
    if not interrupts:
        return None
    first = interrupts[0]
    payload = first.value if hasattr(first, "value") else first
    required_keys = {
        "tool_call_id",
        "model_tool_call_id",
        "tool_name",
        "risk",
        "message",
        "session_id",
    }
    if not isinstance(payload, dict) or not required_keys.issubset(payload):
        return None
    return PendingConfirmation(
        tool_call_id=payload["tool_call_id"],
        model_tool_call_id=payload["model_tool_call_id"],
        tool_name=payload["tool_name"],
        risk=payload["risk"],
        message=payload["message"],
        args_preview=payload.get("args_preview", {}),
        session_id=payload["session_id"],
    )


async def agent_node(state: AgentState) -> dict[str, list[AIMessage]]:
    current_date = datetime.now(ZoneInfo("America/Bogota")).strftime("%A, %d de %B de %Y, %H:%M")
    system_prompt = f"{state['system_prompt']}\n\nFecha y hora actual: {current_date} (hora Colombia)."
    response = await ainvoke_chat_with_fallback([SystemMessage(content=system_prompt), *state["messages"]])
    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        if state.get("tool_iteration_count", 0) >= MAX_TOOL_ITERATIONS:
            return "limit_reached"
        return "tools"
    return "end"


async def limit_reached_node(state: AgentState) -> dict[str, list[AIMessage]]:
    return {"messages": [AIMessage(content=MAX_TOOL_ITERATIONS_LIMIT_MESSAGE)]}


async def tool_executor_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    last_msg = state["messages"][-1]
    if not isinstance(last_msg, AIMessage):
        return {}
    configurable = config.get("configurable", {})
    tool_ctx = configurable.get("tool_ctx", {})
    results: list[ToolMessage] = []
    for tc in last_msg.tool_calls:
        tool_id = tc["name"]
        model_tc_id = tc.get("id") or ""
        args = tc.get("args", {})
        if tool_id not in TOOL_HANDLERS:
            results.append(ToolMessage(content=json.dumps({"error": f"Unknown tool: {tool_id}"}), tool_call_id=model_tc_id))
            continue
        if tool_ctx.get("enabled_tools") and tool_id not in tool_ctx["enabled_tools"]:
            results.append(
                ToolMessage(
                    content=json.dumps({"error": f"Tool not enabled: {tool_id}"}),
                    tool_call_id=model_tc_id,
                )
            )
            continue
        if tool_requires_confirmation(tool_id):
            if state.get("bypass_confirmation"):
                raise ValueError(f"Tool {tool_id} is not safe for unattended cron execution")
            record = await find_or_create_pending_tool_call(
                db=tool_ctx["db"],
                session_id=state["session_id"],
                tool_name=tool_id,
                args=args,
                model_tool_call_id=model_tc_id,
            )
            payload = {
                "tool_call_id": record.id,
                "model_tool_call_id": model_tc_id,
                "tool_name": tool_id,
                "risk": get_tool_risk(tool_id),
                "message": build_confirmation_message(tool_id, args),
                "args_preview": sanitize_args(tool_id, args),
                "session_id": state["session_id"],
            }
            decision = interrupt(payload)
            if decision != "approve":
                await update_tool_call_status(tool_ctx["db"], record.id, "rejected")
                results.append(ToolMessage(content="Acción cancelada por el usuario.", tool_call_id=model_tc_id))
                continue
            await update_tool_call_status(tool_ctx["db"], record.id, "approved")
            result = await TOOL_HANDLERS[tool_id](args, tool_ctx)
            await update_tool_call_status(tool_ctx["db"], record.id, "executed", result)
            results.append(ToolMessage(content=json.dumps(result), tool_call_id=model_tc_id))
            continue

        async def _handler(tool_args: dict[str, Any], *, _tool_id: str = tool_id) -> dict[str, Any]:
            return await TOOL_HANDLERS[_tool_id](tool_args, tool_ctx)

        result = await run_with_tracking(
            db=tool_ctx["db"],
            session_id=state["session_id"],
            tool_id=tool_id,
            args=args,
            handler=_handler,
            model_tool_call_id=model_tc_id or None,
        )
        results.append(ToolMessage(content=json.dumps(result), tool_call_id=model_tc_id))
    return {
        "messages": results,
        "tool_iteration_count": state.get("tool_iteration_count", 0) + 1,
    }


def _build_initial_messages(
    message: str | None, attachment_blocks: list[dict[str, Any]] | None
) -> list[HumanMessage]:
    if not message and not attachment_blocks:
        return []
    if not attachment_blocks:
        return [HumanMessage(content=message)]
    parts: list[str | dict[Any, Any]] = []
    if message:
        parts.append({"type": "text", "text": message})
    parts.extend(attachment_blocks)
    return [HumanMessage(content=parts)]


_app = None


async def _get_graph_app():
    global _app
    if _app is not None:
        return _app
    graph = StateGraph(AgentState)
    graph.add_node("memory_injection", memory_injection_node)
    graph.add_node("compaction", compaction_node)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_executor_node)
    graph.add_node("limit_reached", limit_reached_node)
    graph.add_edge(START, "memory_injection")
    graph.add_edge("memory_injection", "compaction")
    graph.add_edge("compaction", "agent")
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "end": END, "limit_reached": "limit_reached"},
    )
    graph.add_edge("limit_reached", END)
    graph.add_edge("tools", "compaction")
    checkpointer = await get_checkpointer()
    _app = graph.compile(checkpointer=checkpointer)
    return _app


async def warmup_agent_runtime() -> None:
    await _get_graph_app()


async def run_agent(agent_input: AgentInput) -> AgentOutput:
    app = await _get_graph_app()
    tool_ctx = {
        "db": agent_input.db,
        "user_id": agent_input.user_id,
        "session_id": agent_input.session_id,
        "enabled_tools": agent_input.enabled_tools,
    }
    config = augment_invoke_config(
        {"configurable": {"thread_id": agent_input.session_id, "tool_ctx": tool_ctx}},
        user_id=agent_input.user_id,
        session_id=agent_input.session_id,
        is_resume=bool(agent_input.resume_decision),
    )
    if agent_input.resume_decision:
        final_state = await app.ainvoke(Command(resume=agent_input.resume_decision), config=config)
    else:
        initial_messages = _build_initial_messages(agent_input.message, agent_input.attachment_blocks)
        final_state = await app.ainvoke(
            {
                "messages": initial_messages,
                "session_id": agent_input.session_id,
                "user_id": agent_input.user_id,
                "system_prompt": agent_input.system_prompt,
                "compaction_count": 0,
                "compaction_failure_count": 0,
                "tool_iteration_count": 0,
                "bypass_confirmation": agent_input.bypass_confirmation,
            },
            config=config,
        )
    if isinstance(final_state, dict):
        pending = parse_pending_confirmation(final_state)
        if pending:
            return AgentOutput(
                response=pending.message,
                tool_calls=[pending.tool_name],
                pending_confirmation=pending,
            )
    messages = final_state.get("messages", [])
    ai_messages = [m for m in messages if isinstance(m, AIMessage)]
    response = ai_messages[-1].content if ai_messages else ""
    tool_calls = [tc["name"] for m in ai_messages for tc in m.tool_calls]
    return AgentOutput(response=str(response), tool_calls=tool_calls)
