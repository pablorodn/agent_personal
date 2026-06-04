from collections.abc import Awaitable, Callable
from typing import Any

from supabase import AsyncClient

from app.db.queries.tool_calls import create_tool_call, update_tool_call_status

ToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


async def run_with_tracking(
    db: AsyncClient,
    session_id: str,
    tool_id: str,
    args: dict[str, Any],
    handler: ToolHandler,
    model_tool_call_id: str | None = None,
) -> dict[str, Any]:
    record = await create_tool_call(
        db=db,
        session_id=session_id,
        tool_name=tool_id,
        args=args,
        needs_confirmation=False,
        model_tool_call_id=model_tool_call_id,
    )
    try:
        result = await handler(args)
    except Exception:
        await update_tool_call_status(db, record.id, "failed")
        raise
    await update_tool_call_status(db, record.id, "executed", result)
    return result
