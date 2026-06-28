from fastapi import APIRouter, status
from pydantic import BaseModel
from api.user_services.verify_user import verify_user
from api.models.response_models import ResponseModel
from api.utils.jwt_utils import create_access_token
from datetime import timedelta 

user_router = APIRouter(prefix="/user")

class UserLogin(BaseModel):
    username: str 
    password: str


@user_router.post(path="/login", tags=["user"]) # type: ignore
async def login_user(user_login: UserLogin) -> ResponseModel:
    try:
        user = verify_user(user_login.username, user_login.password)
        if user is None:
            return ResponseModel(
                status=status.HTTP_401_UNAUTHORIZED,
                message="incorrect username or password",
                data=None 
            )
        
        token = create_access_token(
            data={
                "user_id": user.user_id,
                "username": user.username
            },
            expires_delta=timedelta(minutes=(60 * 8)),
        )

        return ResponseModel(
            status=status.HTTP_200_OK,
            message="success",
            data={
                "access_token" : token,
                "type": "bearer"
            } 
        )
        
    except Exception as e:
        return ResponseModel(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="there was an issue logging you in try again later",
            data=None 
        )