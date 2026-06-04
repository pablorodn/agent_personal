from app.agent.state import AgentState


async def memory_injection_node(state: AgentState) -> dict:
    # Hook point for long-term memory retrieval; initialized with no-op safe behavior.
    return {"system_prompt": state["system_prompt"]}
