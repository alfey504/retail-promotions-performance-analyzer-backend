from pydantic import BaseModel
from datetime import date
from typing import Optional
from services.db_services.models import Promotion
from datetime import datetime

class PromotionResponse(BaseModel):
    promotion_id: int
    promotion_name: str
    promotion_description: Optional[str]
    discount_percent: Optional[int]
    promotion_type: str
    start_date: date
    end_date: date

    class Config:
        from_attributes = True

class CreateConversationJSONBody(BaseModel):
    promotion_id: int
    promotion_name: str

class ConversationResponse(BaseModel): 
    conversation_id: int
    conversation_title: str
    user_id: int
    created_at: datetime
    promotion_id: int 

    class Config:
        from_attributes = True

class SkuResponse(BaseModel):
    sku_id: int
    product_id: int
    sku_name: str
    size: Optional[str]
    color: Optional[str]
    price: float

    class Config:
        from_attributes = True