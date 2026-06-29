from fastapi import APIRouter, status, Depends
from api.models.response_models import ResponseModel
from api.middleware.auth_middleware import auth_middleware

from services.pipeline_services.pipe import reload_data

data_router = APIRouter(tags=["data"])

@data_router.post("/data/reload", tags=["data"])
async def reload_data(user = Depends(auth_middleware)) -> ResponseModel:
    try:
        reload_data()
        return ResponseModel(
            status = status.HTTP_200_OK,
            message = "success",
            data = None
        )
    except Exception as e:
        print(e)
        return ResponseModel(
            status = status.HTTP_500_INTERNAL_SERVER_ERROR,
            message = "there was an issue while piping data from api to database",
            max_page=0,
            current_page=0,
            data=None
        )
            

