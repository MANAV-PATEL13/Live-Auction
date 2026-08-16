from fastapi import APIRouter, Depends

from src.modules.users.schema import UserGroupsUpdate
from src.modules.users.service import UserService
from src.modules.auth.dependencies import get_current_user, require_permission
from src.modules.users.model import User

from src.common.utils import success_response


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

service = UserService()


@router.get("")
async def get_users(
    current_user: User = Depends(require_permission("user:view")),
):
    users = await service.get_all()

    return success_response(
        code=200,
        message="Users fetched successfully",
        data=users,
    )


@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return success_response(
        code=200,
        message="Current user fetched successfully",
        data={
            "id": str(current_user.id),
            "name": current_user.name,
            "email": current_user.email,
            "is_active": current_user.is_active,
            "is_allowed": current_user.is_allowed,
            "is_superuser": current_user.is_superuser,
        },
    )


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    current_user: User = Depends(require_permission("user:view")),
):
    user = await service.get_by_id(user_id)

    return success_response(
        code=200,
        message="User fetched successfully",
        data=user,
    )


@router.put("/{user_id}/groups")
async def update_user_groups(
    user_id: str,
    data: UserGroupsUpdate,
    current_user: User = Depends(require_permission("user:update")),
):
    user = await service.update_groups(user_id, data)

    return success_response(
        code=200,
        message="User groups updated successfully",
        data=user,
    )


@router.put("/{user_id}/activate")
async def activate_user(
    user_id: str,
    current_user: User = Depends(require_permission("user:access")),
):
    user = await service.reactivate(user_id)

    return success_response(
        code=200,
        message="User activated successfully",
        data=user,
    )


@router.put("/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    current_user: User = Depends(require_permission("user:access")),
):
    user = await service.deactivate(user_id)

    return success_response(
        code=200,
        message="User deactivated successfully",
        data=user,
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_permission("user:delete")),
):
    await service.delete(user_id)

    return success_response(
        code=200,
        message="User deleted successfully",
        data=None,
    )
