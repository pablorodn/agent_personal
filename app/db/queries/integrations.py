from pydantic import BaseModel
from supabase import AsyncClient


class UserIntegration(BaseModel):
    id: str
    user_id: str
    provider: str
    encrypted_tokens: str | None = None
    status: str | None = None


async def get_integration(db: AsyncClient, user_id: str, provider: str) -> UserIntegration | None:
    result = (
        await db.table("user_integrations")
        .select("*")
        .eq("user_id", user_id)
        .eq("provider", provider)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    return UserIntegration(**result.data[0])


async def upsert_integration(
    db: AsyncClient, user_id: str, provider: str, encrypted_tokens: str, status: str = "active"
) -> UserIntegration:
    payload = {
        "user_id": user_id,
        "provider": provider,
        "encrypted_tokens": encrypted_tokens,
        "status": status,
    }
    result = await db.table("user_integrations").upsert(payload).execute()
    return UserIntegration(**result.data[0])


async def disconnect_integration(db: AsyncClient, user_id: str, provider: str) -> None:
    await (
        db.table("user_integrations")
        .update({"status": "revoked"})
        .eq("user_id", user_id)
        .eq("provider", provider)
        .execute()
    )
