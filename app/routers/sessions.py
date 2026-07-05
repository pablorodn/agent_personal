import logging

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from supabase import AsyncClient

from app.agent.checkpointer import get_checkpointer
from app.db.queries.messages import clear_session_messages
from app.db.queries.sessions import (
    archive_session,
    create_session,
    delete_session,
    get_session_by_id,
    list_sessions,
)
from app.dependencies import get_current_user_id, get_db
from app.template_filters import register_template_filters

router = APIRouter(prefix="/api/sessions")
templates = Jinja2Templates(directory="app/templates")
register_template_filters(templates)
logger = logging.getLogger(__name__)


@router.get("")
async def get_sessions(
    request: Request,
    db: AsyncClient = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    sessions = await list_sessions(db, user_id, channel="web")
    return {"sessions": [s.model_dump() for s in sessions]}


@router.post("", response_class=HTMLResponse)
async def post_session(
    request: Request,
    db: AsyncClient = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    session = await create_session(db, user_id, channel="web")
    return templates.TemplateResponse(
        request, "partials/session_item.html", {"request": request, "session": session}
    )


@router.post("/{session_id}/clear")
async def clear_session(
    session_id: str,
    db: AsyncClient = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    session = await get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Session does not belong to user")
    await clear_session_messages(db, session_id)
    return ""


async def _cleanup_checkpointer_thread(session_id: str) -> None:
    try:
        checkpointer = await get_checkpointer()
        await checkpointer.adelete_thread(session_id)
    except Exception as exc:  # pragma: no cover - external services
        logger.warning(
            "Checkpointer thread cleanup skipped due to recoverable error.",
            extra={
                "event": "checkpointer_delete_thread_error",
                "reason": str(exc),
                "session_id": session_id,
            },
        )


@router.post("/{session_id}/archive", response_class=HTMLResponse)
async def archive_session_route(
    session_id: str,
    current_session_id: str = Form(default=""),
    db: AsyncClient = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    session = await get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Session does not belong to user")
    await archive_session(db, session_id)
    if session_id == current_session_id:
        await create_session(db, user_id, channel="web")
        response = HTMLResponse(status_code=200)
        response.headers["HX-Redirect"] = "/chat"
        return response
    return HTMLResponse(content="", status_code=200)


@router.post("/{session_id}/delete", response_class=HTMLResponse)
async def delete_session_route(
    session_id: str,
    current_session_id: str = Form(default=""),
    db: AsyncClient = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    session = await get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Session does not belong to user")
    await _cleanup_checkpointer_thread(session_id)
    await delete_session(db, session_id)
    if session_id == current_session_id:
        await create_session(db, user_id, channel="web")
        response = HTMLResponse(status_code=200)
        response.headers["HX-Redirect"] = "/chat"
        return response
    return HTMLResponse(content="", status_code=200)
