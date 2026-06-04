from datetime import datetime, timezone

from pydantic import BaseModel
from supabase import AsyncClient


class AgentSession(BaseModel):
    id: str
    user_id: str
    channel: str
    status: str
    last_used_at: str | None = None


async def list_sessions(db: AsyncClient, user_id: str, channel: str = "web") -> list[AgentSession]:
    result = (
        await db.table("agent_sessions")
        .select("*")
        .eq("user_id", user_id)
        .eq("channel", channel)
        .eq("status", "active")
        .order("last_used_at", desc=True)
        .execute()
    )
    return [AgentSession(**row) for row in result.data]


async def get_active_session(
    db: AsyncClient, user_id: str, channel: str
) -> AgentSession | None:
    result = (
        await db.table("agent_sessions")
        .select("*")
        .eq("user_id", user_id)
        .eq("channel", channel)
        .eq("status", "active")
        .order("last_used_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    return AgentSession(**result.data[0])


async def create_session(db: AsyncClient, user_id: str, channel: str = "web") -> AgentSession:
    payload = {
        "user_id": user_id,
        "channel": channel,
        "status": "active",
        "last_used_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.table("agent_sessions").insert(payload).execute()
    return AgentSession(**result.data[0])


async def get_or_create_active_session(
    db: AsyncClient, user_id: str, channel: str
) -> AgentSession:
    current = await get_active_session(db, user_id, channel)
    if current:
        return current
    return await create_session(db, user_id, channel)


async def touch_session(db: AsyncClient, session_id: str) -> None:
    await (
        db.table("agent_sessions")
        .update({"last_used_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", session_id)
        .execute()
    )


async def get_session_by_id(db: AsyncClient, session_id: str) -> AgentSession | None:
    result = await db.table("agent_sessions").select("*").eq("id", session_id).limit(1).execute()
    if not result.data:
        return None
    return AgentSession(**result.data[0])
