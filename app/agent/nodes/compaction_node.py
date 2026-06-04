from app.agent.compaction import microcompact, should_compact
from app.agent.state import AgentState


async def compaction_node(state: AgentState) -> dict:
    messages = state["messages"]
    if should_compact(messages):
        return {"messages": microcompact(messages), "compaction_count": state.get("compaction_count", 0) + 1}
    return {}
