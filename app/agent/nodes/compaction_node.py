import logging

from langchain_core.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES

from app.agent.compaction import (
    CIRCUIT_BREAKER_LIMIT,
    llm_compact,
    microcompact,
    should_compact,
)
from app.agent.state import AgentState

logger = logging.getLogger(__name__)


def _replace_messages(messages: list) -> list:
    return [RemoveMessage(id=REMOVE_ALL_MESSAGES), *messages]


async def compaction_node(state: AgentState) -> dict:
    messages = state["messages"]
    if not should_compact(messages):
        return {}

    failure_count = state.get("compaction_failure_count", 0)
    compaction_count = state.get("compaction_count", 0)

    if failure_count >= CIRCUIT_BREAKER_LIMIT:
        compacted = microcompact(messages)
        return {
            "messages": _replace_messages(compacted),
            "compaction_count": compaction_count + 1,
            "compaction_failure_count": failure_count,
        }

    try:
        compacted = await llm_compact(messages)
        return {
            "messages": _replace_messages(compacted),
            "compaction_count": compaction_count + 1,
            "compaction_failure_count": 0,
        }
    except Exception as exc:
        logger.warning(
            "LLM compaction failed; falling back to microcompact.",
            extra={
                "event": "compaction_llm_failed",
                "reason": str(exc),
                "session_id": state.get("session_id"),
                "failure_count": failure_count + 1,
            },
        )
        compacted = microcompact(messages)
        return {
            "messages": _replace_messages(compacted),
            "compaction_count": compaction_count + 1,
            "compaction_failure_count": failure_count + 1,
        }
