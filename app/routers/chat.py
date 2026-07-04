import asyncio
import json
import logging
import time

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from fastapi.templating import Jinja2Templates
from supabase import AsyncClient

from app.agent.graph import AgentInput, run_agent
from app.agent.memory_flush import flush_session_memory
from app.db.queries.messages import add_message
from app.db.queries.profiles import get_profile
from app.db.queries.sessions import get_session_by_id
from app.db.queries.tool_calls import get_pending_tool_call
from app.db.queries.tools import list_enabled_tool_ids
from app.dependencies import get_current_user_id, get_db

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
    db: AsyncClient = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    total_start = time.perf_counter()
    db_start = time.perf_counter()
    clean_message = message.strip()
    if not session_id.strip() or not clean_message:
        return Response(
            content=(
                '<div class="flex justify-start">'
                '<div class="max-w-[80%] rounded-lg bg-amber-100 px-4 py-2.5 text-sm text-amber-900 dark:bg-amber-900/40 dark:text-amber-100">'
                "No pude procesar el mensaje. Verifica la sesion activa e intenta de nuevo."
                "</div></div>"
            ),
            media_type="text/html",
            status_code=400,
        )
    session = await get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Session does not belong to user")
    await add_message(db, session_id, "user", clean_message)
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
    agent_start = time.perf_counter()
    result = await run_agent(
        AgentInput(
            user_id=user_id,
            session_id=session_id,
            system_prompt=system_prompt,
            db=db,
            enabled_tools=enabled_tools,
            message=clean_message,
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
    db: AsyncClient = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    async def _stream():
        total_start = time.perf_counter()
        clean_message = message.strip()
        if not session_id.strip() or not clean_message:
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
        await add_message(db, session_id, "user", clean_message)

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

        agent_start = time.perf_counter()
        agent_task = asyncio.create_task(
            run_agent(
                AgentInput(
                    user_id=user_id,
                    session_id=session_id,
                    system_prompt=system_prompt,
                    db=db,
                    enabled_tools=enabled_tools,
                    message=clean_message,
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
