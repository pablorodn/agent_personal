import asyncio
import logging
from collections.abc import Sequence
from typing import Any

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from app.config import get_settings

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
PRIMARY_CHAT_MODEL = "google/gemini-2.5-flash"
FALLBACK_CHAT_MODEL = "openai/gpt-4o-mini"
CHAT_TIMEOUT_SECONDS = 4.0

logger = logging.getLogger(__name__)


def create_chat_model(model_name: str = PRIMARY_CHAT_MODEL) -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=model_name,
        temperature=0.2,
        max_tokens=220,
        timeout=CHAT_TIMEOUT_SECONDS,
        max_retries=0,
        openai_api_key=settings.openrouter_api_key,
        openai_api_base=OPENROUTER_BASE_URL,
        default_headers={"HTTP-Referer": "https://agents.local"},
    )  # type: ignore[call-arg]


def create_compaction_model() -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model="google/gemini-2.5-flash",
        temperature=0.1,
        openai_api_key=settings.openrouter_api_key,
        openai_api_base=OPENROUTER_BASE_URL,
        default_headers={"HTTP-Referer": "https://agents.local"},
    )  # type: ignore[call-arg]


async def ainvoke_chat_with_fallback(messages: Sequence[Any]) -> AIMessage:
    primary = create_chat_model(PRIMARY_CHAT_MODEL)
    try:
        result = await asyncio.wait_for(primary.ainvoke(messages), timeout=CHAT_TIMEOUT_SECONDS)
        if isinstance(result, AIMessage):
            return result
        return AIMessage(content=str(getattr(result, "content", "")))
    except Exception as exc:
        logger.warning(
            "Primary chat model failed; using fallback.",
            extra={
                "event": "chat_model_fallback",
                "reason": str(exc),
                "primary_model": PRIMARY_CHAT_MODEL,
                "fallback_model": FALLBACK_CHAT_MODEL,
            },
        )

    fallback = create_chat_model(FALLBACK_CHAT_MODEL)
    result = await fallback.ainvoke(messages)
    if isinstance(result, AIMessage):
        return result
    return AIMessage(content=str(getattr(result, "content", "")))
