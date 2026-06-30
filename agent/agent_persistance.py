
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from services.db_services.messages_db import (  
    add_message,
    get_messages_by_conversation_id,
)

_ROLE_FACTORY = {
    "user": HumanMessage,
    "assistant": AIMessage,
}


def _ordered(messages):
    return sorted(
        messages,
        key=lambda m: (m.created_at, getattr(m, "message_id", 0)),
    )


def _load_lc_history_sync(conversation_id: int) -> list[BaseMessage]:
    rows = get_messages_by_conversation_id(conversation_id)
    history: list[BaseMessage] = []
    for row in rows:
        factory = _ROLE_FACTORY.get(row.role)
        if factory is not None:
            history.append(factory(content=row.content))
    return history


def _load_history_payload_sync(conversation_id: int) -> list[dict]:
    rows = get_messages_by_conversation_id(conversation_id)
    return [
        {
            "id": str(row.message_id),
            "role": row.role,
            "content": row.content,
            "timestamp": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


def _save_sync(conversation_id: int, role: str, content: str) -> None:
    add_message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        created_at=datetime.now(timezone.utc),
    )


async def load_lc_history(conversation_id: int) -> list[BaseMessage]:
    """History as LangChain messages, for feeding back into the model."""
    return await asyncio.to_thread(_load_lc_history_sync, conversation_id)


async def load_history_payload(conversation_id: int) -> list[dict]:
    """History as JSON-serialisable dicts, for sending to the client on connect."""
    return await asyncio.to_thread(_load_history_payload_sync, conversation_id)


async def save_user_message(conversation_id: int, content: str) -> None:
    await asyncio.to_thread(_save_sync, conversation_id, "user", content)


async def save_assistant_message(conversation_id: int, content: str) -> None:
    await asyncio.to_thread(_save_sync, conversation_id, "assistant", content)