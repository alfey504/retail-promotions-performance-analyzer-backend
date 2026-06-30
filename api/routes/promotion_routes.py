from fastapi import APIRouter, status, Depends
from api.models.response_models import PagedResponseModel
from services.db_services.promotions_db import get_promotions_as_page
from api.models.data_models import PromotionResponse
from api.middleware.auth_middleware import auth_middleware

promotions_router = APIRouter(tags=["promotions"])

@promotions_router.get("/promotions", tags=["promotions"])
async def get_promotions(page: int=1, user = Depends(auth_middleware)) -> PagedResponseModel:
    print(user)
    page_size = 25
    max_page = int (350 / 25)

    if page < 1 or page > max_page:
        return PagedResponseModel(
            status = status.HTTP_400_BAD_REQUEST,
            message = "please sure the provided page number is within the given range",
            max_page=max_page,
            current_page=page,
            data=None
        )
    
    try:
        promotions_db = get_promotions_as_page(page, page_size)  

        promotions = [
            PromotionResponse.model_validate(promo_db) 
            for promo_db in promotions_db
        ]
        
        
        return PagedResponseModel(
            status = status.HTTP_200_OK,
            message = "success",
            max_page = max_page,
            current_page = page,
            data = promotions
        )
    except Exception as e:
        print(e)
        return PagedResponseModel(
            status = status.HTTP_500_INTERNAL_SERVER_ERROR,
            message = "there was an issue while fetching promotions",
            max_page=0,
            current_page=0,
            data=None
        )
            

