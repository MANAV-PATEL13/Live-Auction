from fastapi import APIRouter

from src.modules.permission_groups.schema import (
    PermissionGroupCreate,
    PermissionGroupUpdate,
)
from src.modules.permission_groups.service import (
    PermissionGroupService,
)


router = APIRouter(
    prefix="/permission-groups",
    tags=["Permission Groups"],
)

service = PermissionGroupService()


@router.post("")
async def create_group(
    data: PermissionGroupCreate,
):

    group = await service.create(data)

    return {
        "success": True,
        "code": 201,
        "message": "Permission group created successfully",
        "data": group,
    }


@router.get("")
async def get_groups():

    groups = await service.get_all()

    return {
        "success": True,
        "code": 200,
        "message": "Permission groups fetched successfully",
        "data": groups,
    }


@router.get("/{group_id}")
async def get_group(
    group_id: str,
):

    group = await service.get_by_id(group_id)

    return {
        "success": True,
        "code": 200,
        "message": "Permission group fetched successfully",
        "data": group,
    }


@router.put("/{group_id}")
async def update_group(
    group_id: str,
    data: PermissionGroupUpdate,
):

    group = await service.update(
        group_id,
        data,
    )

    return {
        "success": True,
        "code": 200,
        "message": "Permission group updated successfully",
        "data": group,
    }


@router.delete("/{group_id}")
async def delete_group(
    group_id: str,
):

    await service.delete(group_id)

    return {
        "success": True,
        "code": 200,
        "message": "Permission group deleted successfully",
        "data": None,
    }