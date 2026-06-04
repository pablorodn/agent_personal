from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from supabase import AsyncClient

from app.db.queries.integrations import get_integration
from app.db.queries.profiles import get_profile, upsert_profile
from app.db.queries.telegram import is_telegram_linked
from app.db.queries.tools import list_enabled_tool_ids, replace_enabled_tools
from app.dependencies import get_current_user_id, get_db
from app.tools.catalog import TOOL_CATALOG

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    db: AsyncClient = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    profile = await get_profile(db, user_id)
    enabled_tool_ids = await list_enabled_tool_ids(db, user_id)
    github_integration = await get_integration(db, user_id, "github")
    telegram_linked = await is_telegram_linked(db, user_id)
    profile_payload = {
        "name": profile.name if profile and profile.name else "",
        "agent_name": profile.agent_name if profile and profile.agent_name else "Agente",
        "agent_system_prompt": (
            profile.agent_system_prompt
            if profile and profile.agent_system_prompt
            else ""
        ),
    }
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "request": request,
            "active_nav": "settings",
            "agent_name": profile_payload["agent_name"],
            "profile": profile_payload,
            "tool_catalog": TOOL_CATALOG,
            "enabled_tool_ids": enabled_tool_ids,
            "github_connected": bool(
                github_integration and github_integration.status == "active"
            ),
            "telegram_linked": telegram_linked,
            "link_code": None,
        },
    )


@router.post("/settings", response_class=HTMLResponse)
async def settings_save(
    request: Request,
    db: AsyncClient = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    name: str = Form(default=""),
    agent_name: str = Form(default=""),
    system_prompt: str = Form(default=""),
    enabled_tools: list[str] = Form(default=[]),
):
    await upsert_profile(
        db,
        {
            "id": user_id,
            "name": name,
            "agent_name": agent_name,
            "agent_system_prompt": system_prompt,
        },
    )
    catalog_ids = {tool.id for tool in TOOL_CATALOG}
    selected_tool_ids = [tool_id for tool_id in enabled_tools if tool_id in catalog_ids]
    await replace_enabled_tools(db, user_id, selected_tool_ids)
    return templates.TemplateResponse(request, "partials/settings_save_status.html", {"request": request})
