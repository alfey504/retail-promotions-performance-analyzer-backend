from pydantic import BaseModel
from datetime import date
from typing import Optional
from services.db_services.models import Promotion

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
    
