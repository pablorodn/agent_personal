import logging

from langchain_core.messages import HumanMessage, SystemMessage
from supabase import AsyncClient

from app.agent.model import create_compaction_model
from app.db.queries.messages import AgentMessage, get_session_messages
from app.db.queries.sessions import update_session_title

logger = logging.getLogger(__name__)

TITLE_MAX_WORDS = 6

TITLE_SYSTEM_PROMPT = (
    f"Genera un titulo corto (maximo {TITLE_MAX_WORDS} palabras, sin comillas "
    "ni punto final) para una conversacion, a partir de su primer mensaje de "
    "usuario. Responde unicamente con el titulo, sin explicaciones."
)


def _first_texted_user_message(messages: list[AgentMessage]) -> str | None:
    for message in messages:
        if message.role != "user":
            continue
        content = (message.content or "").strip()
        if content:
            return content
    return None


def _clean_title(raw: str) -> str:
    title = raw.strip()
    if len(title) >= 2 and title[0] in "\"'" and title[-1] in "\"'":
        title = title[1:-1].strip()
    title = title.rstrip(".").strip()
    return " ".join(title.split()[:TITLE_MAX_WORDS])


async def generate_session_title(db: AsyncClient, session_id: str) -> None:
    try:
        messages = await get_session_messages(db, session_id)
        seed_message = _first_texted_user_message(messages)
        if seed_message is None:
            return
        model = create_compaction_model()
        response = await model.ainvoke(
            [
                SystemMessage(content=TITLE_SYSTEM_PROMPT),
                HumanMessage(content=f"Mensaje del usuario:\n{seed_message}"),
            ]
        )
        title = _clean_title(str(getattr(response, "content", "")))
        if not title:
            return
        await update_session_title(db, session_id, title)
    except Exception as exc:  # pragma: no cover - external services
        logger.warning(
            "Session title generation skipped due to recoverable error.",
            extra={
                "event": "session_title_error",
                "reason": str(exc),
                "session_id": session_id,
            },
        )
