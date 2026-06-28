from fastapi import Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from jose import jwt, JWTError
from api.utils.jwt_utils import verify_access_token
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/user/login")


async def auth_middleware(token: str = Depends(oauth2_scheme)):
    data = verify_access_token(token)
    if data is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    return data