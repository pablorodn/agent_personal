import secrets
from typing import Any

import httpx

from app.config import get_settings


def generate_link_code() -> str:
    return secrets.token_hex(4).upper()


async def set_webhook() -> dict:
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_webhook_base_url:
        return {"ok": False, "reason": "TELEGRAM config missing"}
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/setWebhook"
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            url,
            json={
                "url": f"{settings.telegram_webhook_base_url}/api/telegram/webhook",
                "secret_token": settings.telegram_webhook_secret,
            },
        )
        return response.json()


async def send_text_message(
    chat_id: int,
    text: str,
    reply_markup: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.telegram_bot_token:
        return {"ok": False, "description": "TELEGRAM_BOT_TOKEN missing"}
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


async def answer_callback_query(callback_query_id: str, text: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    if not settings.telegram_bot_token:
        return {"ok": False, "description": "TELEGRAM_BOT_TOKEN missing"}
    payload: dict[str, Any] = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/answerCallbackQuery"
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


def build_hitl_keyboard(tool_call_id: str) -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "Aprobar", "callback_data": f"confirm_approve:{tool_call_id}"},
                {"text": "Cancelar", "callback_data": f"confirm_reject:{tool_call_id}"},
            ]
        ]
    }


def parse_confirmation_callback(data: str) -> tuple[str, str] | None:
    if data.startswith("confirm_approve:"):
        return ("approve", data.split(":", 1)[1])
    if data.startswith("confirm_reject:"):
        return ("reject", data.split(":", 1)[1])
    return None
