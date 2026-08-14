from fastapi import APIRouter

from src.modules.permissions.schema import (
    PermissionCreate,
    PermissionUpdate,
)
from src.modules.permissions.service import PermissionService

from src.common.utils import success_response


router = APIRouter(
    prefix="/permissions",
    tags=["Permissions"],
)

service = PermissionService()


@router.post("")
async def create_permission(
    data: PermissionCreate,
):
    permission = await service.create(data)

    return success_response(
        code= 201,
        message= "Permission created successfully",
        data= permission,
    )


@router.get("")
async def get_permissions():

    permissions = await service.get_all()

    return success_response(
        code= 200,
        message= "Permissions fetched successfully",
        data= permissions,
    )


@router.get("/{permission_id}")
async def get_permission(
    permission_id: str,
):

    permission = await service.get_by_id(
        permission_id
    )

    return success_response(
        code= 200,
        message= "Permission fetched successfully",
        data= permission,
    )


@router.put("/{permission_id}")
async def update_permission(
    permission_id: str,
    data: PermissionUpdate,
):

    permission = await service.update(
        permission_id,
        data,
    )

    return success_response(
        code= 200,
        message= "Permission updated successfully",
        data= permission,
    )
    


@router.delete("/{permission_id}")
async def delete_permission(
    permission_id: str,
):

    await service.delete(permission_id)

    return success_response(
        code= 200,
        message= "Permission deleted successfully",
        data= None,
    )