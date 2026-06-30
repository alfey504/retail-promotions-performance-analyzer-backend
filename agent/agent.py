from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI

from agent.agent_graph_state import AgentState
from agent.agent_prompt import build_kickoff_instruction, build_system_prompt
from agent.agent_persistance import (
    load_lc_history,
    save_assistant_message,
    save_user_message,
)

from tools.tools import tools
TOOLS = tools


@lru_cache(maxsize=1)
def get_graph():
    """Build & compile the graph once, then reuse it across all sockets."""
    model = ChatOpenAI(
        model="gpt-oss-120b",
        api_key= os.getenv("CEREBRAS_API_KEY"),
        base_url="https://api.cerebras.ai/v1",
        default_headers={
            "X-Cerebras-3rd-Party-Integration": "langgraph"
        }
    )
    model_with_tools = model.bind_tools(TOOLS)

    async def agent_node(state: AgentState) -> dict:
        response = await model_with_tools.ainvoke(state["messages"])
        return {"messages": [response]}

    builder = StateGraph(AgentState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", ToolNode(TOOLS))

    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "agent")

    return builder.compile()


def _coerce_int(value, field: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an integer, got {value!r}") from exc


def _coerce_optional_int(value) -> Optional[int]:
    if value in (None, "", "null", "None"):
        return None
    return _coerce_int(value, "promotion_id")


def _build_initial_state(
    user_id: int,
    conversation_id: int,
    promotion_id: Optional[int],
    history: list,
    message: str,
) -> AgentState:
    return {
        "messages": [
            SystemMessage(build_system_prompt(promotion_id)),
            *history,
            HumanMessage(message),
        ],
        "user_id": user_id,
        "conversation_id": conversation_id,
        "promotion_id": promotion_id,
    }


async def process_message(
    user_id,
    conversation_id,
    message: str,
    promotion_id,
) -> str:
    """Run one turn and return the assistant's final answer as a string."""
    user_id = _coerce_int(user_id, "user_id")
    conversation_id = _coerce_int(conversation_id, "conversation_id")
    promotion_id = _coerce_optional_int(promotion_id)

    history = await load_lc_history(conversation_id)
    await save_user_message(conversation_id, message)

    state = _build_initial_state(user_id, conversation_id, promotion_id, history, message)
    result = await get_graph().ainvoke(state)

    final = result["messages"][-1]
    answer = final.content if isinstance(final.content, str) else str(final.content)

    await save_assistant_message(conversation_id, answer)
    return answer


async def generate_initial_analysis(
    user_id,
    conversation_id,
    promotion_id,
) -> str:
    """Run an autonomous opening analysis for a freshly opened conversation.

    Call this when the socket connects, history is empty, and a promotion is in
    context. The agent looks up the promotion and runs the KPI tools on its own,
    then we persist the result as the first assistant message (so reconnects show
    it and don't re-trigger). The hidden kickoff instruction is NOT saved.
    """
    user_id = _coerce_int(user_id, "user_id")
    conversation_id = _coerce_int(conversation_id, "conversation_id")
    promotion_id = _coerce_optional_int(promotion_id)
    if promotion_id is None:
        raise ValueError("generate_initial_analysis requires a promotion_id")

    state: AgentState = {
        "messages": [
            SystemMessage(build_system_prompt(promotion_id)),
            HumanMessage(build_kickoff_instruction(promotion_id)),
        ],
        "user_id": user_id,
        "conversation_id": conversation_id,
        "promotion_id": promotion_id,
    }
    result = await get_graph().ainvoke(state)

    final = result["messages"][-1]
    answer = final.content if isinstance(final.content, str) else str(final.content)

    await save_assistant_message(conversation_id, answer)
    return answer