from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel
from supabase import AsyncClient


class ToolCall(BaseModel):
    id: str
    session_id: str
    tool_name: str
    status: str
    requires_confirmation: bool = False
    model_tool_call_id: str | None = None
    result_json: dict[str, Any] | None = None
    arguments_json: dict[str, Any] | None = None


async def create_tool_call(
    db: AsyncClient,
    session_id: str,
    tool_name: str,
    args: dict[str, Any],
    needs_confirmation: bool,
    model_tool_call_id: str | None,
) -> ToolCall:
    payload = {
        "session_id": session_id,
        "tool_name": tool_name,
        "arguments_json": args,
        "status": "pending_confirmation" if needs_confirmation else "executed",
        "requires_confirmation": needs_confirmation,
        "model_tool_call_id": model_tool_call_id,
    }
    result = await db.table("tool_calls").insert(payload).execute()
    return ToolCall(**result.data[0])


async def update_tool_call_status(
    db: AsyncClient,
    tool_call_id: str,
    status: str,
    result_payload: dict[str, Any] | None = None,
) -> None:
    update_data: dict[str, Any] = {"status": status}
    if result_payload is not None:
        update_data["result_json"] = result_payload
    if status in {"rejected", "executed", "failed"}:
        update_data["finished_at"] = datetime.now(timezone.utc).isoformat()
    await db.table("tool_calls").update(update_data).eq("id", tool_call_id).execute()


async def get_tool_call(db: AsyncClient, tool_call_id: str) -> ToolCall | None:
    result = await db.table("tool_calls").select("*").eq("id", tool_call_id).limit(1).execute()
    if not result.data:
        return None
    return ToolCall(**result.data[0])


async def get_pending_tool_call(db: AsyncClient, tool_call_id: str) -> ToolCall | None:
    result = (
        await db.table("tool_calls")
        .select("*")
        .eq("id", tool_call_id)
        .eq("status", "pending_confirmation")
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    return ToolCall(**result.data[0])


async def find_or_create_pending_tool_call(
    db: AsyncClient,
    session_id: str,
    tool_name: str,
    args: dict[str, Any],
    model_tool_call_id: str,
) -> ToolCall:
    existing = (
        await db.table("tool_calls")
        .select("*")
        .eq("session_id", session_id)
        .eq("model_tool_call_id", model_tool_call_id)
        .eq("status", "pending_confirmation")
        .limit(1)
        .execute()
    )
    if existing.data:
        return ToolCall(**existing.data[0])
    return await create_tool_call(
        db=db,
        session_id=session_id,
        tool_name=tool_name,
        args=args,
        needs_confirmation=True,
        model_tool_call_id=model_tool_call_id,
    )


async def has_pending_confirmation_for_session(db: AsyncClient, session_id: str) -> bool:
    result = (
        await db.table("tool_calls")
        .select("id")
        .eq("session_id", session_id)
        .eq("status", "pending_confirmation")
        .limit(1)
        .execute()
    )
    return bool(result.data)
