from datetime import datetime, timezone

from supabase import AsyncClient


async def create_scheduled_task(
    db: AsyncClient,
    user_id: str,
    prompt: str,
    run_at: str | None = None,
    cron_expr: str | None = None,
    timezone: str = "UTC",
) -> dict:
    schedule_type = "recurring" if cron_expr else "one_time"
    next_run_at = run_at
    payload = {
        "user_id": user_id,
        "prompt": prompt,
        "schedule_type": schedule_type,
        "run_at": run_at,
        "cron_expr": cron_expr,
        "timezone": timezone,
        "status": "active",
        "next_run_at": next_run_at,
    }
    result = await db.table("scheduled_tasks").insert(payload).execute()
    return result.data[0]


async def create_task_run(db: AsyncClient, task_id: str, agent_session_id: str) -> dict:
    result = await db.table("scheduled_task_runs").insert(
        {"task_id": task_id, "agent_session_id": agent_session_id, "status": "running"}
    ).execute()
    return result.data[0]


async def complete_task_run(db: AsyncClient, run_id: str, output: str) -> None:
    await (
        db.table("scheduled_task_runs")
        .update(
            {
                "status": "completed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "error": None,
            }
        )
        .eq("id", run_id)
        .execute()
    )


async def fail_task_run(db: AsyncClient, run_id: str, error: str) -> None:
    await (
        db.table("scheduled_task_runs")
        .update(
            {
                "status": "failed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "error": error,
            }
        )
        .eq("id", run_id)
        .execute()
    )


async def update_scheduled_task_after_run(
    db: AsyncClient,
    task_id: str,
    *,
    next_run_at: str | None,
    last_run_at: str,
    status: str,
) -> None:
    await (
        db.table("scheduled_tasks")
        .update({"next_run_at": next_run_at, "last_run_at": last_run_at, "status": status})
        .eq("id", task_id)
        .execute()
    )
