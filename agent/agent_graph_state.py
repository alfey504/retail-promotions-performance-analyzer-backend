"""Graph state for the promotions-analytics agent."""

from __future__ import annotations

from typing import Annotated, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: int
    conversation_id: int
    promotion_id: Optional[int]