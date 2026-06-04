from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel
from supabase import AsyncClient


class AgentMessage(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    structured_payload: dict[str, Any] | None = None


async def add_message(
    db: AsyncClient,
    session_id: str,
    role: str,
    content: str,
    structured_payload: dict[str, Any] | None = None,
) -> AgentMessage:
    payload: dict[str, Any] = {
        "session_id": session_id,
        "role": role,
        "content": content,
        "structured_payload": structured_payload,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.table("agent_messages").insert(payload).execute()
    return AgentMessage(**result.data[0])


async def get_session_messages(db: AsyncClient, session_id: str) -> list[AgentMessage]:
    result = (
        await db.table("agent_messages")
        .select("*")
        .eq("session_id", session_id)
        .order("created_at", desc=False)
        .execute()
    )
    return [AgentMessage(**row) for row in result.data]


async def clear_session_messages(db: AsyncClient, session_id: str) -> None:
    await db.table("agent_messages").delete().eq("session_id", session_id).execute()
