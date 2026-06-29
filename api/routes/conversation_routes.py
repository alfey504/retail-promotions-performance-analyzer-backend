from fastapi import APIRouter, Depends, status, WebSocket, WebSocketDisconnect
from api.middleware.auth_middleware import auth_middleware
from api.models.data_models import CreateConversationJSONBody, ConversationResponse
from api.models.response_models import ResponseModel
from datetime import datetime
from api.utils.jwt_utils import verify_access_token

from services.db_services.conversation_db import create_conversation, conversation_by_user_id
from services.db_services.messages_db import get_messages_by_conversation_id


conversation_router = APIRouter()

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
        messages = get_messages_by_conversation_id(conversation_id_int)
        await web_socket.send_json(messages)
    except Exception as e:
        print(e)
        await web_socket.close(code=500, reason="there was an issue connecting to conversation")

    
    await web_socket.accept()
    user = {
        "user_id": "1"
    }
    try:
        while True:
            user_message = await web_socket.receive_text()
            llm_response = await process_message(
                user_id = user["user_id"],
                conversation_id = conversation_id,
                message = user_message,
                promotion_id = promotion_id,   
            )
            await web_socket.send_text(llm_response)
    except WebSocketDisconnect:
        print(f"conversation disconnected {conversation_id}")

    


async def process_message(
    user_id: str, 
    conversation_id: str, 
    message: str, 
    promotion_id: str
) -> str:
    return "son"