from fastapi import APIRouter, Depends

from src.modules.permission_groups.schema import (
    PermissionGroupCreate,
    PermissionGroupUpdate,
)
from src.modules.permission_groups.service import (
    PermissionGroupService,
)
from src.modules.auth.dependencies import require_permission
from src.modules.users.model import User

from src.common.utils import success_response


router = APIRouter(
    prefix="/permission-groups",
    tags=["Permission Groups"],
)

service = PermissionGroupService()


@router.post("")
async def create_group(
    data: PermissionGroupCreate,
    current_user: User = Depends(require_permission("permission_group:create")),
):
    group = await service.create(data)

    return success_response(
        code=201,
        message="Permission group created successfully",
        data=group,
    )


@router.get("")
async def get_groups(
    current_user: User = Depends(require_permission("permission_group:read")),
):
    groups = await service.get_all()

    return success_response(
        code=200,
        message="Permission groups fetched successfully",
        data=groups,
    )


@router.get("/{group_id}")
async def get_group(
    group_id: str,
    current_user: User = Depends(require_permission("permission_group:read")),
):
    group = await service.get_by_id(group_id)

    return success_response(
        code=200,
        message="Permission group fetched successfully",
        data=group,
    )


@router.put("/{group_id}")
async def update_group(
    group_id: str,
    data: PermissionGroupUpdate,
    current_user: User = Depends(require_permission("permission_group:update")),
):
    group = await service.update(
        group_id,
        data,
    )

    return success_response(
        code=200,
        message="Permission group updated successfully",
        data=group,
    )


@router.delete("/{group_id}")
async def delete_group(
    group_id: str,
    current_user: User = Depends(require_permission("permission_group:delete")),
):
    await service.delete(group_id)

    return success_response(
        code=200,
        message="Permission group deleted successfully",
        data=None,
    )