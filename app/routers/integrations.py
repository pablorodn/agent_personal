from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from supabase import AsyncClient

from app.config import get_settings
from app.db.crypto import encrypt
from app.db.queries.integrations import disconnect_integration, upsert_integration
from app.dependencies import get_current_user_id, get_db
from app.services.oauth_state import build_oauth_state

router = APIRouter(prefix="/api/integrations")
templates = Jinja2Templates(directory="app/templates")


@router.get("/github")
async def github_start():
    settings = get_settings()
    if not settings.github_client_id:
        raise HTTPException(status_code=400, detail="GITHUB_CLIENT_ID missing")
    state = build_oauth_state()
    params = urlencode(
        {
            "client_id": settings.github_client_id,
            "redirect_uri": "http://localhost:8000/api/integrations/github/callback",
            "scope": "repo",
            "state": state,
        }
    )
    response = RedirectResponse(url=f"https://github.com/login/oauth/authorize?{params}")
    response.set_cookie("github_oauth_state", state, httponly=True, secure=False, samesite="lax", max_age=600)
    return response


@router.get("/github/callback")
async def github_callback(
    request: Request,
    code: str,
    state: str,
    db: AsyncClient = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    expected = request.cookies.get("github_oauth_state")
    if not expected or expected != state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    encrypted = encrypt(f"oauth_code:{code}")
    await upsert_integration(db, user_id=user_id, provider="github", encrypted_tokens=encrypted)
    response = RedirectResponse(url="/settings?github=connected", status_code=307)
    response.delete_cookie("github_oauth_state")
    return response


@router.post("/github/disconnect")
async def github_disconnect(
    request: Request,
    db: AsyncClient = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    await disconnect_integration(db, user_id, "github")
    return templates.TemplateResponse(
        request, "partials/github_disconnected_block.html", {"request": request}
    )
