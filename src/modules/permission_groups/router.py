from fastapi import APIRouter, Depends, UploadFile, File

from src.modules.permission_groups.schema import (
    PermissionGroupCreate,
    PermissionGroupUpdate,
    GroupAssignUsersRequest,
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
    group = await service.create(data, current_user)

    return success_response(
        code=201,
        message="Permission group created successfully",
        data=group,
    )


@router.get("")
async def get_groups(
    current_user: User = Depends(require_permission("permission_group:view")),
):
    groups = await service.get_all()

    return success_response(
        code=200,
        message="Permission groups fetched successfully",
        data=groups,
    )


@router.get("/export")
async def export_groups(
    current_user: User = Depends(require_permission("permission_group:view")),
):
    return await service.export_csv()


@router.get("/import/template")
async def download_groups_template(
    current_user: User = Depends(require_permission("permission_group:view")),
):
    import io
    from fastapi.responses import StreamingResponse

    csv_content = (
        "name,description,permissions,is_active\n"
        "Auction Administrator,Full permissions to control auction sessions,auction:view;auction:start;auction:pause;auction:end;auction:bid;auction:sell;auction:rollback;auction:update,true\n"
        "User Coordinator,Permission group for user onboarding and approvals,user:view;user:create;user:update;user:access,true\n"
        "Display Screen,View only access for live stage projector,auction:view;teams:view,true\n"
    )

    return StreamingResponse(
        io.BytesIO(csv_content.encode("utf-8-sig")),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="permission_groups_import_template.csv"'
        },
    )


@router.post("/import")
async def import_groups(
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission("permission_group:create")),
):
    if not file.filename:
        return success_response(
            code=400,
            message="CSV file is required",
            data=None,
        )

    if not file.filename.lower().endswith(".csv"):
        return success_response(
            code=400,
            message="Only CSV files are allowed",
            data=None,
        )

    content = await file.read()
    result = await service.import_csv(content, current_user)

    return success_response(
        code=200,
        message="Permission groups CSV import completed",
        data=result,
    )


@router.get("/{group_id}")
async def get_group(
    group_id: str,
    current_user: User = Depends(require_permission("permission_group:view")),
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
        current_user,
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


@router.get("/{group_id}/users")
async def get_group_users(
    group_id: str,
    current_user: User = Depends(require_permission("permission_group:view")),
):
    users = await service.get_group_users(group_id)

    return success_response(
        code=200,
        message="Group users fetched successfully",
        data=users,
    )


@router.post("/{group_id}/users")
async def assign_users_to_group(
    group_id: str,
    data: GroupAssignUsersRequest,
    current_user: User = Depends(require_permission("permission_group:update")),
):
    result = await service.assign_users(group_id, data.user_ids)

    return success_response(
        code=200,
        message="Users assigned to permission group successfully",
        data=result,
    )