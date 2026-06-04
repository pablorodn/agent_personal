from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from supabase import AsyncClient

from app.agent.graph import AgentInput, run_agent
from app.config import get_settings
from app.db.crypto import decrypt
from app.db.queries.integrations import get_integration
from app.db.queries.messages import add_message, clear_session_messages
from app.db.queries.profiles import get_profile
from app.db.queries.sessions import (
    create_session,
    get_or_create_active_session,
    get_session_by_id,
    list_sessions,
    touch_session,
)
from app.db.queries.telegram import (
    create_link_code,
    get_link_code,
    get_telegram_account_by_telegram_user_id,
    link_telegram_account,
    mark_link_code_used,
)
from app.db.queries.tool_calls import get_pending_tool_call
from app.db.queries.tools import list_enabled_tool_ids
from app.dependencies import get_current_user_id, get_db
from app.services.telegram_bot import (
    answer_callback_query,
    build_hitl_keyboard,
    generate_link_code,
    parse_confirmation_callback,
    send_text_message,
    set_webhook,
)

router = APIRouter(prefix="/api/telegram")
templates = Jinja2Templates(directory="app/templates")


def _is_expired(expires_at: str) -> bool:
    parsed = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    return parsed <= datetime.now(timezone.utc)


async def _handle_link_command(
    db: AsyncClient,
    telegram_user_id: int,
    chat_id: int,
    text: str,
) -> None:
    parts = text.strip().split(maxsplit=1)
    if len(parts) != 2 or not parts[1]:
        await send_text_message(chat_id, "Uso correcto: /link CODIGO")
        return
    code = parts[1].strip().upper()
    link_code = await get_link_code(db, code)
    if not link_code:
        await send_text_message(chat_id, "Código inválido.")
        return
    if bool(link_code.get("used")):
        await send_text_message(chat_id, "Este código ya fue utilizado.")
        return
    expires_at = str(link_code.get("expires_at", ""))
    if not expires_at or _is_expired(expires_at):
        await send_text_message(chat_id, "Código expirado. Genera uno nuevo desde Ajustes.")
        return
    await link_telegram_account(
        db,
        user_id=str(link_code["user_id"]),
        telegram_user_id=str(telegram_user_id),
        chat_id=str(chat_id),
    )
    await mark_link_code_used(db, str(link_code["id"]))
    await send_text_message(chat_id, "Cuenta vinculada correctamente. Ya puedes escribir mensajes.")


async def _run_telegram_agent_turn(
    db: AsyncClient,
    *,
    user_id: str,
    session_id: str,
    chat_id: int,
    message: str | None = None,
    resume_decision: str | None = None,
) -> None:
    profile = await get_profile(db, user_id)
    if not profile:
        await send_text_message(chat_id, "No se encontró tu perfil. Completa onboarding en web.")
        return
    enabled_tools = await list_enabled_tool_ids(db, user_id)
    github_integration = await get_integration(db, user_id, "github")
    github_token: str | None = None
    integrations: list[str] = []
    if github_integration and github_integration.status == "active":
        integrations = ["github"]
        if github_integration.encrypted_tokens:
            github_token = decrypt(github_integration.encrypted_tokens)
    result = await run_agent(
        AgentInput(
            user_id=user_id,
            session_id=session_id,
            system_prompt=profile.agent_system_prompt or "Eres un asistente útil.",
            db=db,
            enabled_tools=enabled_tools,
            integrations=integrations,
            message=message,
            resume_decision=resume_decision,
            github_token=github_token,
        )
    )
    structured_payload = None
    reply_markup = None
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
        reply_markup = build_hitl_keyboard(result.pending_confirmation.tool_call_id)
    await add_message(db, session_id, "assistant", result.response, structured_payload=structured_payload)
    await send_text_message(chat_id, result.response, reply_markup=reply_markup)


async def _handle_command(
    db: AsyncClient,
    *,
    user_id: str,
    chat_id: int,
    text: str,
) -> bool:
    command = text.strip()
    if command == "/sessions":
        sessions = await list_sessions(db, user_id=user_id, channel="telegram")
        if not sessions:
            await send_text_message(chat_id, "No tienes sesiones. Usa /new para crear una.")
            return True
        lines = ["Tus sesiones activas:"]
        for idx, session in enumerate(sessions, start=1):
            lines.append(f"{idx}. {session.id}")
        lines.append("Usa /switch N para cambiar.")
        await send_text_message(chat_id, "\n".join(lines))
        return True
    if command == "/new":
        session = await create_session(db, user_id=user_id, channel="telegram")
        await send_text_message(chat_id, f"Nueva sesión creada. ID: {session.id}")
        return True
    if command.startswith("/switch"):
        parts = command.split(maxsplit=1)
        if len(parts) != 2 or not parts[1].isdigit():
            await send_text_message(chat_id, "Uso correcto: /switch N")
            return True
        index = int(parts[1])
        sessions = await list_sessions(db, user_id=user_id, channel="telegram")
        if index < 1 or index > len(sessions):
            await send_text_message(chat_id, "Índice de sesión inválido.")
            return True
        selected = sessions[index - 1]
        await touch_session(db, selected.id)
        await send_text_message(chat_id, "Sesión activa cambiada.")
        return True
    if command == "/clear":
        session = await get_or_create_active_session(db, user_id=user_id, channel="telegram")
        await clear_session_messages(db, session.id)
        await send_text_message(chat_id, "Sesión limpiada.")
        return True
    return False


@router.post("/webhook")
async def webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
    db: AsyncClient = Depends(get_db),
):
    settings = get_settings()
    if settings.telegram_webhook_secret and x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    update = await request.json()
    callback_query = update.get("callback_query")
    if callback_query:
        callback_id = str(callback_query.get("id", ""))
        data = str(callback_query.get("data", ""))
        parsed = parse_confirmation_callback(data)
        message_obj = callback_query.get("message", {}) or {}
        chat = message_obj.get("chat", {}) or {}
        from_user = callback_query.get("from", {}) or {}
        chat_id = int(chat.get("id", 0))
        telegram_user_id = int(from_user.get("id", 0))
        if callback_id:
            await answer_callback_query(callback_id)
        account = await get_telegram_account_by_telegram_user_id(db, str(telegram_user_id))
        if not account:
            await send_text_message(chat_id, "Primero vincula tu cuenta con /link CODIGO")
            return {"ok": True}
        if not parsed:
            return {"ok": True}
        action, tool_call_id = parsed
        tool_call = await get_pending_tool_call(db, tool_call_id)
        if not tool_call:
            await send_text_message(chat_id, "La confirmación ya no está pendiente.")
            return {"ok": True}
        session = await get_session_by_id(db, tool_call.session_id)
        if not session or session.user_id != str(account["user_id"]):
            await send_text_message(chat_id, "No tienes permisos para esta confirmación.")
            return {"ok": True}
        await _run_telegram_agent_turn(
            db,
            user_id=str(account["user_id"]),
            session_id=tool_call.session_id,
            chat_id=chat_id,
            resume_decision=action,
        )
        return {"ok": True}

    message = update.get("message")
    if not message:
        return {"ok": True}
    chat = message.get("chat", {}) or {}
    from_user = message.get("from", {}) or {}
    chat_id = int(chat.get("id", 0))
    telegram_user_id = int(from_user.get("id", 0))
    text = str(message.get("text", "")).strip()
    if not text:
        return {"ok": True}

    if text.startswith("/link"):
        await _handle_link_command(db, telegram_user_id=telegram_user_id, chat_id=chat_id, text=text)
        return {"ok": True}

    account = await get_telegram_account_by_telegram_user_id(db, str(telegram_user_id))
    if not account:
        await send_text_message(chat_id, "Primero vincula tu cuenta con /link CODIGO")
        return {"ok": True}

    handled_command = await _handle_command(
        db,
        user_id=str(account["user_id"]),
        chat_id=chat_id,
        text=text,
    )
    if handled_command:
        return {"ok": True}

    session = await get_or_create_active_session(db, user_id=str(account["user_id"]), channel="telegram")
    await touch_session(db, session.id)
    await add_message(db, session.id, "user", text)
    await _run_telegram_agent_turn(
        db,
        user_id=str(account["user_id"]),
        session_id=session.id,
        chat_id=chat_id,
        message=text,
    )
    return {"ok": True}


@router.get("/setup")
async def setup():
    return await set_webhook()


@router.post("/generate-code", response_class=HTMLResponse)
async def generate_code(
    request: Request,
    db: AsyncClient = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    code = generate_link_code()
    await create_link_code(db, user_id=user_id, code=code)
    return templates.TemplateResponse(
        request, "partials/telegram_link_code.html", {"request": request, "link_code": code}
    )
