from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from supabase import AsyncClient

from app.agent.graph import AgentInput, run_agent
from app.config import get_settings
from app.db.crypto import decrypt
from app.db.queries.integrations import get_integration
from app.db.queries.profiles import get_profile
from app.db.queries.scheduled_tasks import (
    complete_task_run,
    create_task_run,
    fail_task_run,
    update_scheduled_task_after_run,
)
from app.db.queries.sessions import get_or_create_active_session
from app.db.queries.tools import list_enabled_tool_ids
from app.dependencies import get_db
from app.services.cron_claim import claim_due_tasks
from app.services.scheduler import compute_next_run_at

router = APIRouter(prefix="/api/cron")


@router.post("/scheduled-tasks")
async def run_scheduled_tasks(
    authorization: str | None = Header(default=None),
    db: AsyncClient = Depends(get_db),
):
    settings = get_settings()
    if settings.cron_secret and authorization != f"Bearer {settings.cron_secret}":
        raise HTTPException(status_code=401, detail="Invalid cron secret")
    tasks = await claim_due_tasks()
    processed = 0
    failed = 0
    for task in tasks:
        profile = await get_profile(db, task["user_id"])
        if not profile:
            continue
        enabled_tools = await list_enabled_tool_ids(db, task["user_id"])
        github_integration = await get_integration(db, task["user_id"], "github")
        github_token: str | None = None
        if github_integration and github_integration.encrypted_tokens:
            github_token = decrypt(github_integration.encrypted_tokens)
        cron_session = await get_or_create_active_session(db, task["user_id"], channel="cron")
        run = await create_task_run(db, task_id=task["id"], agent_session_id=cron_session.id)
        try:
            result = await run_agent(
                AgentInput(
                    user_id=task["user_id"],
                    session_id=cron_session.id,
                    system_prompt=profile.agent_system_prompt or "Eres un asistente útil.",
                    db=db,
                    enabled_tools=enabled_tools,
                    integrations=["github"] if github_integration and github_integration.status == "active" else [],
                    message=task["prompt"],
                    github_token=github_token,
                    bypass_confirmation=True,
                )
            )
            await complete_task_run(db, run["id"], result.response)
            if task.get("schedule_type") == "recurring" and task.get("cron_expr"):
                next_run_at = compute_next_run_at(task["cron_expr"], task.get("timezone") or "UTC")
                await update_scheduled_task_after_run(
                    db,
                    task["id"],
                    next_run_at=next_run_at,
                    last_run_at=datetime.now(timezone.utc).isoformat(),
                    status="active",
                )
            else:
                await update_scheduled_task_after_run(
                    db,
                    task["id"],
                    next_run_at=None,
                    last_run_at=datetime.now(timezone.utc).isoformat(),
                    status="completed",
                )
            processed += 1
        except Exception as exc:
            await fail_task_run(db, run["id"], str(exc))
            await update_scheduled_task_after_run(
                db,
                task["id"],
                next_run_at=task.get("next_run_at"),
                last_run_at=datetime.now(timezone.utc).isoformat(),
                status="active",
            )
            failed += 1
    return {"ok": True, "processed": processed, "failed": failed}
