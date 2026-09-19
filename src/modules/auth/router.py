from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.jwt import decode_token
from src.common.utils import success_response
from src.modules.auth.schema import LoginRequest, RefreshTokenRequest
from src.modules.auth.service import AuthService
from src.modules.users.schema import UserCreate
from src.modules.users.service import UserService

from src.modules.auth.dependencies import get_current_user
from src.modules.users.model import User

from src.modules.sessions.repository import SessionRepository
from beanie import PydanticObjectId

from src.common.exceptions import InvalidTokenException

router = APIRouter(
    prefix = '/auth',
    tags = ["Authentication"]
)


user_service = UserService()
auth_service = AuthService()
session_repository = SessionRepository()



@router.post("/register")
async def register(data: UserCreate):

    user = await user_service.create_user(data)

    return success_response(
        message="User registered successfully",
        data={
            "id" : str(user.id),
            "name" : user.name,
            "email" : user.email
        }
    )


@router.post("/login")
async def login(data : LoginRequest):

    access_token, refresh_token = await auth_service.login(
        email=data.email,
        password=data.password,
        device_id = data.device_id,
        device_name=data.device_name,
        platform=data.platform
    )

    return success_response(
        message="Login successful",
        data={
            "access_token" : access_token,
            "refresh_token" : refresh_token,
        }
    )

@router.post("/logout")
async def logout(
    current_user : User = Depends(get_current_user),
    credentials : HTTPAuthorizationCredentials = Depends(
        HTTPBearer()
    )
):

    token = credentials.credentials

    payload = decode_token(token)
    
    session_id = payload.get("session_id")

    await auth_service.logout(
        PydanticObjectId(session_id)
    )
    
    return success_response(
        message="Logout successful",
        data=None
    )

@router.post("/refresh")
async def refresh_token(
    data: RefreshTokenRequest,
):

    access_token = await auth_service.refresh_access_token(
        data.refresh_token
    )

    return success_response(
        message="Access token refreshed successfully",
        data={
            "access_token": access_token,
            "token_type": "bearer",
        },
    )