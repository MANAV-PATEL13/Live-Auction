from fastapi import APIRouter, Depends

from src.common.utils import success_response
from src.modules.auth.schema import LoginRequest, RefreshTokenRequest
from src.modules.auth.service import AuthService
from src.modules.users.schema import UserCreate
from src.modules.users.service import UserService

from src.modules.auth.dependencies import get_current_user
from src.modules.users.model import User

router = APIRouter(
    prefix = '/auth',
    tags = ["Authentication"]
)


user_service = UserService()
auth_service = AuthService()


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

@router.get("/login")
async def login(data : LoginRequest):

    access_token, refresh_token = await auth_service.login(
        email=data.email,
        password=data.password,
    )

    return success_response(
        message="Login successful",
        data={
            "access_token" : access_token,
            "refresh_token" : refresh_token,
        }
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


@router.get("/me")
async def get_me(
    current_user : User = Depends(get_current_user),
):

    return success_response(
        message="User fetched Successfully",
        data={
            "id" : str(current_user.id),
            "name" : current_user.name,
            "email" : current_user.email,
        }
    )