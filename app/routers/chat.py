import asyncio
import json
import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from fastapi.templating import Jinja2Templates
from supabase import AsyncClient

from app.agent.graph import AgentInput, run_agent
from app.agent.memory_flush import flush_session_memory
from app.agent.model import validate_model_selection
from app.db.queries.messages import add_message
from app.db.queries.profiles import get_profile, upsert_profile
from app.db.queries.sessions import get_session_by_id
from app.db.queries.tool_calls import get_pending_tool_call
from app.db.queries.tools import list_enabled_tool_ids
from app.dependencies import get_current_user_id, get_db
from app.services.attachments import (
    AttachmentValidationError,
    build_attachment_blocks,
    real_attachments,
)

router = APIRouter(prefix="/api")
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)
LATENCY_STYLE_SUFFIX = (
    "\n\n[ESTILO DE RESPUESTA]\n"
    "Prioriza velocidad: responde de forma breve y directa (maximo 3 frases y aprox. 80 palabras), "
    "salvo que el usuario pida explicitamente una respuesta extensa."
)


def _sse(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=True)}\n\n"


def _error_fragment(message: str) -> str:
    return (
        '<div class="flex justify-start">'
        '<div class="max-w-[80%] rounded-lg bg-amber-100 px-4 py-2.5 text-sm text-amber-900 dark:bg-amber-900/40 dark:text-amber-100">'
        f"{message}"
        "</div></div>"
    )


def _attachment_note_payload(count: int, kinds: list[str]) -> dict[str, Any] | None:
    if not kinds:
        return None
    return {"type": "attachment_note", "count": count, "kinds": kinds}


def _resolve_chat_model(
    requested_model: str, stored_default_model: str | None, *, db: AsyncClient, user_id: str
) -> str:
    resolved = validate_model_selection(requested_model.strip() or stored_default_model, user_id=user_id)
    if resolved != stored_default_model:
        asyncio.create_task(_persist_default_model(db=db, user_id=user_id, model_name=resolved))
    return resolved


async def _persist_default_model(db: AsyncClient, user_id: str, model_name: str) -> None:
    try:
        await upsert_profile(db, {"id": user_id, "default_model": model_name})
    except Exception as exc:  # pragma: no cover - external services
        logger.warning(
            "Default model preference persistence skipped due to recoverable error.",
            extra={
                "event": "default_model_persist_error",
                "reason": str(exc),
                "user_id": user_id,
                "model_name": model_name,
            },
        )


def _build_user_system_prompt(
    base_prompt: str,
    *,
    user_name: str | None,
    language: str | None,
    timezone: str | None,
) -> str:
    """Append authenticated profile context to the agent prompt."""
    context_lines: list[str] = []
    if user_name:
        context_lines.append(f"Nombre del usuario autenticado: {user_name}.")
    if language:
        context_lines.append(f"Idioma preferido del usuario: {language}.")
    if timezone:
        context_lines.append(f"Zona horaria del usuario: {timezone}.")
    if not context_lines:
        return f"{base_prompt}{LATENCY_STYLE_SUFFIX}"
    context_block = "\n".join(context_lines)
    return f"{base_prompt}\n\n[CONTEXTO DE PERFIL]\n{context_block}{LATENCY_STYLE_SUFFIX}"


@router.post("/chat", response_class=HTMLResponse)
async def chat(
    request: Request,
    message: str = Form(""),
    session_id: str = Form(""),
    chat_model: str = Form(""),
    attachments: list[UploadFile] = File(default=[]),
    db: AsyncClient = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    total_start = time.perf_counter()
    db_start = time.perf_counter()
    clean_message = message.strip()
    files = real_attachments(attachments)
    if not session_id.strip() or (not clean_message and not files):
        return Response(
            content=_error_fragment(
                "No pude procesar el mensaje. Verifica la sesion activa e intenta de nuevo."
            ),
            media_type="text/html",
            status_code=400,
        )
    session = await get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Session does not belong to user")
    try:
        attachment_blocks, kinds = await build_attachment_blocks(files)
    except AttachmentValidationError as exc:
        return Response(content=_error_fragment(str(exc)), media_type="text/html", status_code=400)
    await add_message(
        db,
        session_id,
        "user",
        clean_message,
        structured_payload=_attachment_note_payload(len(files), kinds),
    )
    profile, enabled_tools = await asyncio.gather(
        get_profile(db, user_id),
        list_enabled_tool_ids(db, user_id),
    )
    db_ms = round((time.perf_counter() - db_start) * 1000, 2)
    base_prompt = (
        profile.agent_system_prompt
        if profile and profile.agent_system_prompt
        else "Eres un asistente útil."
    )
    system_prompt = _build_user_system_prompt(
        base_prompt,
        user_name=profile.name if profile else None,
        language=profile.language if profile else None,
        timezone=profile.timezone if profile else None,
    )
    resolved_chat_model = _resolve_chat_model(
        chat_model,
        getattr(profile, "default_model", None) if profile else None,
        db=db,
        user_id=user_id,
    )
    agent_start = time.perf_counter()
    result = await run_agent(
        AgentInput(
            user_id=user_id,
            session_id=session_id,
            system_prompt=system_prompt,
            db=db,
            enabled_tools=enabled_tools,
            chat_model=resolved_chat_model,
            message=clean_message,
            attachment_blocks=attachment_blocks or None,
        )
    )
    agent_ms = round((time.perf_counter() - agent_start) * 1000, 2)
    structured_payload = None
    if result.pending_confirmation:
        structured_payload = {
            "type": "pending_confirmation",
            "tool_call_id": result.pending_confirmation.tool_call_id,
            "model_tool_call_id": result.pending_confirmation.model_tool_call_id,
            "tool_name": result.pending_confirmation.tool_name,
            "risk": result.pending_confirmation.risk,
            "args_preview": result.pending_confirmation.args_preview,
            "confirmation_status": "pending",
        }
    msg = await add_message(
        db,
        session_id,
        "assistant",
        result.response,
        structured_payload=structured_payload,
    )
    if not result.pending_confirmation:
        asyncio.create_task(flush_session_memory(db=db, user_id=user_id, session_id=session_id))
    logger.info(
        "Chat message processed.",
        extra={
            "event": "chat_processed",
            "request_id": getattr(request.state, "request_id", None),
            "session_id": session_id,
            "user_id": user_id,
            "db_ms": db_ms,
            "agent_ms": agent_ms,
            "total_ms": round((time.perf_counter() - total_start) * 1000, 2),
        },
    )
    return templates.TemplateResponse(request, "partials/message.html", {"request": request, "msg": msg})


@router.post("/chat/stream")
async def chat_stream(
    request: Request,
    message: str = Form(""),
    session_id: str = Form(""),
    chat_model: str = Form(""),
    attachments: list[UploadFile] = File(default=[]),
    db: AsyncClient = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    async def _stream():
        total_start = time.perf_counter()
        clean_message = message.strip()
        files = real_attachments(attachments)
        if not session_id.strip() or (not clean_message and not files):
            yield _sse(
                "error",
                {"message": "No pude procesar el mensaje. Verifica la sesion activa e intenta de nuevo."},
            )
            return
        session = await get_session_by_id(db, session_id)
        if not session:
            yield _sse("error", {"message": "Sesion no encontrada."})
            return
        if session.user_id != user_id:
            yield _sse("error", {"message": "Sesion invalida para este usuario."})
            return
        try:
            attachment_blocks, kinds = await build_attachment_blocks(files)
        except AttachmentValidationError as exc:
            yield _sse("error", {"message": str(exc)})
            return
        await add_message(
            db,
            session_id,
            "user",
            clean_message,
            structured_payload=_attachment_note_payload(len(files), kinds),
        )

        db_start = time.perf_counter()
        profile, enabled_tools = await asyncio.gather(
            get_profile(db, user_id),
            list_enabled_tool_ids(db, user_id),
        )
        db_ms = round((time.perf_counter() - db_start) * 1000, 2)
        yield _sse("status", {"phase": "context_ready", "db_ms": db_ms})

        base_prompt = (
            profile.agent_system_prompt
            if profile and profile.agent_system_prompt
            else "Eres un asistente útil."
        )
        system_prompt = _build_user_system_prompt(
            base_prompt,
            user_name=profile.name if profile else None,
            language=profile.language if profile else None,
            timezone=profile.timezone if profile else None,
        )
        resolved_chat_model = _resolve_chat_model(
            chat_model,
            getattr(profile, "default_model", None) if profile else None,
            db=db,
            user_id=user_id,
        )

        agent_start = time.perf_counter()
        agent_task = asyncio.create_task(
            run_agent(
                AgentInput(
                    user_id=user_id,
                    session_id=session_id,
                    system_prompt=system_prompt,
                    db=db,
                    enabled_tools=enabled_tools,
                    chat_model=resolved_chat_model,
                    message=clean_message,
                    attachment_blocks=attachment_blocks or None,
                )
            )
        )
        while not agent_task.done():
            elapsed_ms = round((time.perf_counter() - agent_start) * 1000, 2)
            yield _sse("tick", {"phase": "generating", "elapsed_ms": elapsed_ms})
            await asyncio.sleep(0.35)

        try:
            result = await agent_task
        except Exception as exc:
            logger.exception(
                "Chat stream failed during agent execution.",
                extra={
                    "event": "chat_stream_error",
                    "request_id": getattr(request.state, "request_id", None),
                    "reason": str(exc),
                },
            )
            yield _sse("error", {"message": "No pude generar la respuesta. Intenta de nuevo."})
            return
        agent_ms = round((time.perf_counter() - agent_start) * 1000, 2)

        structured_payload = None
        if result.pending_confirmation:
            structured_payload = {
                "type": "pending_confirmation",
                "tool_call_id": result.pending_confirmation.tool_call_id,
                "model_tool_call_id": result.pending_confirmation.model_tool_call_id,
                "tool_name": result.pending_confirmation.tool_name,
                "risk": result.pending_confirmation.risk,
                "args_preview": result.pending_confirmation.args_preview,
                "confirmation_status": "pending",
            }
        msg = await add_message(
            db,
            session_id,
            "assistant",
            result.response,
            structured_payload=structured_payload,
        )
        if not result.pending_confirmation:
            asyncio.create_task(flush_session_memory(db=db, user_id=user_id, session_id=session_id))

        html = templates.get_template("partials/message.html").render({"request": request, "msg": msg})
        total_ms = round((time.perf_counter() - total_start) * 1000, 2)
        logger.info(
            "Chat stream processed.",
            extra={
                "event": "chat_stream_processed",
                "request_id": getattr(request.state, "request_id", None),
                "session_id": session_id,
                "user_id": user_id,
                "db_ms": db_ms,
                "agent_ms": agent_ms,
                "total_ms": total_ms,
            },
        )
        yield _sse("message_html", {"html": html, "total_ms": total_ms, "agent_ms": agent_ms})

    return StreamingResponse(_stream(), media_type="text/event-stream")


@router.post("/chat/confirm", response_class=HTMLResponse)
async def chat_confirm(
    request: Request,
    tool_call_id: str = Form(...),
    action: str = Form(...),
    db: AsyncClient = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    if action not in {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="Invalid action")
    tool_call = await get_pending_tool_call(db, tool_call_id)
    if not tool_call:
        raise HTTPException(status_code=404, detail="Tool call not found")
    session = await get_session_by_id(db, tool_call.session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Tool call does not belong to user")
    profile, enabled_tools = await asyncio.gather(
        get_profile(db, user_id),
        list_enabled_tool_ids(db, user_id),
    )
    base_prompt = (
        profile.agent_system_prompt
        if profile and profile.agent_system_prompt
        else "Eres un asistente útil."
    )
    system_prompt = _build_user_system_prompt(
        base_prompt,
        user_name=profile.name if profile else None,
        language=profile.language if profile else None,
        timezone=profile.timezone if profile else None,
    )
    result = await run_agent(
        AgentInput(
            user_id=user_id,
            session_id=tool_call.session_id,
            system_prompt=system_prompt,
            db=db,
            enabled_tools=enabled_tools,
            resume_decision=action,
        )
    )
    msg = await add_message(db, tool_call.session_id, "assistant", result.response)
    return templates.TemplateResponse(request, "partials/message.html", {"request": request, "msg": msg})
