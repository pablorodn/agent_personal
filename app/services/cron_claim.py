import asyncpg

from app.config import get_settings


async def claim_due_tasks(limit: int = 20) -> list[dict]:
    settings = get_settings()
    conn = await asyncpg.connect(settings.database_url)
    try:
        rows = await conn.fetch(
            """
            WITH due AS (
                SELECT id
                FROM public.scheduled_tasks
                WHERE status = 'active'
                  AND next_run_at IS NOT NULL
                  AND next_run_at <= NOW()
                ORDER BY next_run_at ASC
                FOR UPDATE SKIP LOCKED
                LIMIT $1
            )
            UPDATE public.scheduled_tasks t
            SET status = 'paused'
            FROM due
            WHERE t.id = due.id
            RETURNING t.*;
            """,
            limit,
        )
        return [dict(row) for row in rows]
    finally:
        await conn.close()
