from datetime import datetime, timedelta, timezone

from supabase import AsyncClient


async def create_link_code(db: AsyncClient, user_id: str, code: str) -> None:
    await db.table("telegram_link_codes").insert(
        {
            "user_id": user_id,
            "code": code,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        }
    ).execute()


async def get_link_code(db: AsyncClient, code: str) -> dict | None:
    result = await db.table("telegram_link_codes").select("*").eq("code", code).limit(1).execute()
    return result.data[0] if result.data else None


async def mark_link_code_used(db: AsyncClient, link_code_id: str) -> None:
    await (
        db.table("telegram_link_codes")
        .update({"used": True})
        .eq("id", link_code_id)
        .execute()
    )


async def link_telegram_account(db: AsyncClient, user_id: str, telegram_user_id: str, chat_id: str) -> None:
    await db.table("telegram_accounts").upsert(
        {"user_id": user_id, "telegram_user_id": telegram_user_id, "chat_id": chat_id}
    ).execute()


async def is_telegram_linked(db: AsyncClient, user_id: str) -> bool:
    result = await db.table("telegram_accounts").select("id").eq("user_id", user_id).limit(1).execute()
    return bool(result.data)


async def get_telegram_account_by_telegram_user_id(
    db: AsyncClient, telegram_user_id: str
) -> dict | None:
    result = (
        await db.table("telegram_accounts")
        .select("*")
        .eq("telegram_user_id", telegram_user_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None
