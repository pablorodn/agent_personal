from langfuse.langchain import CallbackHandler

from app.config import get_settings


def create_langfuse_callback() -> CallbackHandler | None:
    settings = get_settings()
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return None
    return CallbackHandler()
