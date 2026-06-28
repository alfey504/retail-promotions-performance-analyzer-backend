from fastapi import APIRouter, Depends, status
from api.middleware.auth_middleware import auth_middleware
from api.models.data_models import CreateConversationJSONBody, ConversationResponse
from api.models.response_models import ResponseModel
from datetime import datetime

from services.db_services.conversation_db import create_conversation

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

        