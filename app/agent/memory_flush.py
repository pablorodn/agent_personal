import logging

from supabase import AsyncClient

from app.agent.embeddings import generate_embedding
from app.agent.memory_classifier import classify_memory_type
from app.db.queries.memories import save_memory
from app.db.queries.messages import get_session_messages
from app.services.memory_policy import can_store_memory

logger = logging.getLogger(__name__)


async def flush_session_memory(db: AsyncClient, user_id: str, session_id: str) -> None:
    try:
        messages = await get_session_messages(db, session_id)
        if not messages:
            return
        last_user_message = next((m for m in reversed(messages) if m.role == "user"), None)
        if last_user_message is None:
            return
        latest = (last_user_message.content or "").strip()
        if not latest:
            return
        if not can_store_memory(latest):
            return
        memory_type = await classify_memory_type(latest)
        embedding = await generate_embedding(latest)
        await save_memory(db, user_id=user_id, memory_type=memory_type, content=latest, embedding=embedding)
    except Exception as exc:  # pragma: no cover - external services
        logger.warning(
            "Memory flush skipped due to recoverable error.",
            extra={
                "event": "memory_flush_error",
                "reason": str(exc),
                "user_id": user_id,
                "session_id": session_id,
            },
        )
