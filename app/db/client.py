from supabase import AsyncClient, create_async_client

from app.config import get_settings


async def create_server_client() -> AsyncClient:
    settings = get_settings()
    return await create_async_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )


async def create_browser_client(access_token: str) -> AsyncClient:
    settings = get_settings()
    client = await create_async_client(settings.supabase_url, settings.supabase_anon_key)
    client.postgrest.auth(access_token)
    return client
