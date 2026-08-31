from fastapi import APIRouter, Depends
from beanie import PydanticObjectId

from src.common.utils import success_response
from src.modules.auth.dependencies import get_current_user, require_permission
from src.modules.sessions.repository import SessionRepository
from src.modules.users.model import User


router = APIRouter(
    prefix="/sessions",
    tags=["Sessions"],
)

repository = SessionRepository()


@router.get("/history")
async def get_login_history(
    current_user: User = Depends(get_current_user),
):

    sessions = await repository.get_user_history(
        current_user.id
    )

    return success_response(
        message="Login history fetched successfully",
        data=sessions,
    )

@router.get("/history/{user_id}")
async def get_login_history(
    user_id : PydanticObjectId,
    current_user: User = Depends(
            require_permission("sessions:view")
        ),
):

    sessions = await repository.get_user_history(
        user_id
    )

    return success_response(
        message="Login history fetched successfully",
        data=sessions,
    )