from langchain_core.messages import BaseMessage

CHARS_PER_TOKEN = 4
CONTEXT_WINDOW_TOKENS = 128_000
COMPACTION_THRESHOLD = 0.8
COMPACTION_TAIL_SIZE = 10


def estimate_tokens(messages: list[BaseMessage]) -> int:
    total_chars = sum(len(str(msg.content)) for msg in messages)
    return total_chars // CHARS_PER_TOKEN


def should_compact(messages: list[BaseMessage]) -> bool:
    return estimate_tokens(messages) >= int(CONTEXT_WINDOW_TOKENS * COMPACTION_THRESHOLD)


def microcompact(messages: list[BaseMessage]) -> list[BaseMessage]:
    if len(messages) <= COMPACTION_TAIL_SIZE:
        return messages
    return messages[-COMPACTION_TAIL_SIZE:]
