from fastapi import APIRouter, Depends, status
from api.models.response_models import ResponseModel
from api.models.data_models import SkuResponse
from api.middleware.auth_middleware import auth_middleware
from services.db_services.sku_db import get_all_skus


sku_router = APIRouter()

@sku_router.get("/skus", tags=["skus"])
def fetch_all_skus(user = Depends(auth_middleware)) -> ResponseModel:
    try:
        skus_db = get_all_skus()
        skus: list[SkuResponse] = []
        for sku_db in skus_db:
            sku = SkuResponse.model_validate(sku_db)
            skus.append(sku)
        return ResponseModel(
            status = status.HTTP_200_OK,
            message="success",
            data=skus
        )
    except Exception as e:
        print(e)
        return ResponseModel(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="there was an issue while retrieving skus",
            data=None
        )



        