from __future__ import annotations
import asyncio 
from fastapi import APIRouter, Depends, status, WebSocket, WebSocketDisconnect
from api.middleware.auth_middleware import auth_middleware
from api.models.data_models import CreateConversationJSONBody, ConversationResponse
from api.models.response_models import ResponseModel
from datetime import datetime
from api.utils.jwt_utils import verify_access_token

from services.db_services.conversation_db import create_conversation, conversation_by_user_id, conversation_by_id
from services.db_services.messages_db import get_messages_by_conversation_id

from agent.agent_persistance import load_history_payload
from agent.agent import generate_initial_analysis, process_message

conversation_router = APIRouter()

_EMPTY_PROMO = {"", "null", "None", "undefined"}

def _parse_promotion_param(value: str) -> int | None:
    if value in _EMPTY_PROMO:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
    
@conversation_router.post("/conversation", tags=["conversations"])
async def create_new_conversation(
    promotion: CreateConversationJSONBody, 
    user = Depends(auth_middleware)
) -> ResponseModel:
    
    created_at = datetime.now()
    conversation_title = f"{promotion.promotion_id}-{promotion.promotion_name}-{created_at}" 
    try:
        conversation = create_conversation(
            conversation_title = conversation_title, 
            user_id = user["user_id"], 
            created_at = created_at,
            promotion_id = promotion.promotion_id,
        )

        conversation = ConversationResponse.model_validate(conversation)
        return ResponseModel(
            status=status.HTTP_200_OK,
            message="success",
            data = conversation 
        )
        
    except Exception as e:
        print(e)
        return ResponseModel(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="there was an issue while creating your conversation",
            data = None 
        )
    
@conversation_router.get("/conversations", tags=["conversations"])
def get_users_conversation(user = Depends(auth_middleware)) -> ResponseModel:
    user_id = user["user_id"]
    try:
        conversations_db = conversation_by_user_id(user_id)
        conversations: list[ConversationResponse]= []

        for conversation_db in conversations_db:
            conversation = ConversationResponse.model_validate(conversation_db)
            conversations.append(conversation)

        return ResponseModel(
            status=status.HTTP_200_OK,
            message="success",
            data = conversations
        ) 
    except Exception as e:
        print(e)
        return ResponseModel(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="there was an issue while fetching your conversation",
            data = None 
        )


def _parse_promotion_param(value: str) -> int | None:
    if value in _EMPTY_PROMO:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
 
 
@conversation_router.websocket("/ws/conversation/{conversation_id}/{promotion_id}")
async def conversation_socket(
    web_socket: WebSocket,
    conversation_id: str,
    promotion_id: str,
):
    token = web_socket.query_params.get("token")
    if not token:
        await web_socket.close(code=1008)
        return
 
    user = verify_access_token(token)
    if user is None:
        await web_socket.close(code=1008)
        return
 
    try:
        conversation_id_int = int(conversation_id)
    except ValueError:
        await web_socket.close(code=1008)
        return
 
    conversation = await asyncio.to_thread(conversation_by_id, conversation_id_int)
    if conversation is None or conversation.user_id != user["user_id"]:
        await web_socket.close(code=1008)
        return
 
    promotion_id_value = conversation.promotion_id
    if promotion_id_value is None:
        promotion_id_value = _parse_promotion_param(promotion_id)
 
    await web_socket.accept()
 
    try:
        history = await load_history_payload(conversation_id_int)
        await web_socket.send_json({"type": "history", "messages": history})
    except Exception:
        print("failed loading history for conversation %s", conversation_id_int)
        await web_socket.close(code=1011)
        return
 
    if not history and promotion_id_value is not None:
        try:
            insight = await generate_initial_analysis(
                user["user_id"], conversation_id_int, promotion_id_value
            )
            await web_socket.send_json(
                {"type": "message", "role": "assistant", "content": insight}
            )
        except Exception:
            print("initial analysis failed for conversation %s", conversation_id_int)
            await web_socket.send_json(
                {"type": "error", "content": "Could not generate the initial analysis."}
            )
 
    try:
        while True:
            user_message = await web_socket.receive_text()
            try:
                reply = await process_message(
                    user_id=user["user_id"],
                    conversation_id=conversation_id_int,
                    message=user_message,
                    promotion_id=promotion_id_value,
                )
                await web_socket.send_json(
                    {"type": "message", "role": "assistant", "content": reply}
                )
            except Exception:
                print("error handling message in conversation %s", conversation_id_int)
                await web_socket.send_json(
                    {"type": "error", "content": "Something went wrong handling that message."}
                )
    except WebSocketDisconnect:
        print("conversation disconnected %s", conversation_id_int)
 
