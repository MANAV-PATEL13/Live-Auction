from fastapi import APIRouter

from src.common.utils import success_response
from src.modules.auth.schema import LoginRequest
from src.modules.auth.service import AuthService
from src.modules.users.schema import UserCreate
from src.modules.users.service import UserService


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


@router.get("/login")
async def login(data: LoginRequest):

    user = await auth_service.authenticate(
        data.email,
        data.password
    )

    if not user:
        return{
            "success": False,
            "code": 401,
            "message": "Invalid email or password",
            "data": None,
            "errors": None
        }

    return success_response(
        message="Login successfuly...",
        data={
            "name" : user.name,
            "email" : user.email
        }
    )