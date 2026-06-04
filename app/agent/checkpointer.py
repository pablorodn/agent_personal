import logging
from typing import Any, cast
from urllib.parse import urlparse

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg.rows import DictRow, dict_row

from app.config import get_settings

logger = logging.getLogger(__name__)

_saver: AsyncPostgresSaver | None = None
_conn: AsyncConnection[DictRow] | None = None


async def get_checkpointer() -> AsyncPostgresSaver:
    global _saver
    global _conn
    if _saver is None:
        settings = get_settings()
        try:
            dsn = settings.normalized_database_url
            parsed = urlparse(dsn)
            if not parsed.scheme or not parsed.hostname:
                raise ValueError("DATABASE_URL missing scheme or hostname")
            _conn = cast(
                AsyncConnection[DictRow],
                await AsyncConnection.connect(
                    dsn,
                    autocommit=True,
                    prepare_threshold=0,
                    row_factory=cast(Any, dict_row),
                ),
            )
            postgres_saver = AsyncPostgresSaver(_conn)
            await postgres_saver.setup()
            _saver = postgres_saver
        except Exception as exc:  # pragma: no cover - depends on local infra
            logger.error(
                "Postgres checkpointer initialization failed.",
                extra={
                    "event": "checkpointer_init_error",
                    "reason": str(exc),
                    "database_host": settings.database_host,
                },
            )
            raise RuntimeError("Postgres checkpointer unavailable. Verify DATABASE_URL and database connectivity.") from exc
    return _saver
