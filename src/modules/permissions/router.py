from fastapi import APIRouter, Depends, UploadFile, File

from src.modules.permissions.schema import (
    PermissionCreate,
    PermissionUpdate,
)
from src.modules.permissions.service import PermissionService
from src.modules.auth.dependencies import require_permission
from src.modules.users.model import User

from src.common.utils import success_response


router = APIRouter(
    prefix="/permissions",
    tags=["Permissions"],
)

service = PermissionService()


@router.post("")
async def create_permission(
    data: PermissionCreate,
    current_user: User = Depends(require_permission("permission:create")),
):
    permission = await service.create(data, current_user)

    return success_response(
        code=201,
        message="Permission created successfully",
        data=permission,
    )


@router.get("")
async def get_permissions(
    current_user: User = Depends(require_permission("permission:view")),
):
    permissions = await service.get_all()

    return success_response(
        code=200,
        message="Permissions fetched successfully",
        data=permissions,
    )


@router.get("/export")
async def export_permissions(
    current_user: User = Depends(require_permission("permission:view")),
):
    return await service.export_csv()


@router.get("/import/template")
async def download_permissions_template(
    current_user: User = Depends(require_permission("permission:view")),
):
    import io
    from fastapi.responses import StreamingResponse

    csv_content = (
        "name,code,description,is_active\n"
        "Create User,user:create,Permission to create new user accounts,true\n"
        "View User,user:view,Permission to view user profiles and listings,true\n"
        "Update User,user:update,Permission to modify user details and permissions,true\n"
        "Delete User,user:delete,Permission to delete user accounts,true\n"
        "Create Permission,permission:create,Permission to define new system permissions,true\n"
        "View Permission,permission:view,Permission to view permissions catalog,true\n"
        "Update Permission,permission:update,Permission to modify system permissions,true\n"
        "Delete Permission,permission:delete,Permission to delete system permissions,true\n"
        "Create Permission Group,permission_group:create,Permission to create role permission groups,true\n"
        "View Permission Group,permission_group:view,Permission to view role permission groups,true\n"
        "Update Permission Group,permission_group:update,Permission to update role permission groups,true\n"
        "Delete Permission Group,permission_group:delete,Permission to delete role permission groups,true\n"
        "User Access,user:access,Permission to toggle user access and account activation,true\n"
        "Create Canteen Item,canteen:item:create,Permission to create canteen menu items,true\n"
        "View Canteen Item,canteen:item:view,Permission to view canteen menu items,true\n"
        "Update Canteen Item,canteen:item:update,Permission to update canteen menu items,true\n"
        "Delete Canteen Item,canteen:item:delete,Permission to delete canteen menu items,true\n"
        "Create Team,team:create,Permission to create new teams,true\n"
        "Update Team,team:update,Permission to update team metadata and balance,true\n"
        "View Team,team:view,Permission to view teams and rosters,true\n"
        "Delete Team,team:delete,Permission to delete teams,true\n"
        "AppConfig View,appconfig:view,Permission to view application system settings,true\n"
        "AppConfig Update,appconfig:update,Permission to modify application system settings,true\n"
        "Session history View,sessions:view,Permission to view active and past user device sessions,true\n"
        "Registration View,registration:view,Permission to view participant registrations and responses,true\n"
        "Registration Update,registration:update,Permission to update import or manage registrations,true\n"
        "Assign Team,team:assign,Permission to manually assign transfer or remove players from teams,true\n"
        "Auction start,auction:start,Permission to initialize and start live auction sessions,true\n"
        "Auction Pause,auction:pause,Permission to pause and resume active auction sessions,true\n"
        "Auction End,auction:end,Permission to officially end auction sessions,true\n"
        "Auction Sell,auction:sell,Permission to award and sell current player to winning team,true\n"
        "Auction Rollback,auction:rollback,Permission to rollback bids or sold auction outcomes,true\n"
        "Auction Update,auction:update,Permission to update player queue bidding state and quick add players,true\n"
        "Auction View,auction:view,Permission to view live auction control screens and floor state,true\n"
    )

    return StreamingResponse(
        io.BytesIO(csv_content.encode("utf-8-sig")),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="permissions_import_template.csv"'
        },
    )


@router.post("/import")
async def import_permissions(
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission("permission:create")),
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
        message="Permissions CSV import completed",
        data=result,
    )


@router.get("/{permission_id}")
async def get_permission(
    permission_id: str,
    current_user: User = Depends(require_permission("permission:view")),
):
    permission = await service.get_by_id(permission_id)

    return success_response(
        code=200,
        message="Permission fetched successfully",
        data=permission,
    )


@router.put("/{permission_id}")
async def update_permission(
    permission_id: str,
    data: PermissionUpdate,
    current_user: User = Depends(require_permission("permission:update")),
):
    permission = await service.update(
        permission_id,
        data,
        current_user,
    )

    return success_response(
        code=200,
        message="Permission updated successfully",
        data=permission,
    )


@router.delete("/{permission_id}")
async def delete_permission(
    permission_id: str,
    current_user: User = Depends(require_permission("permission:delete")),
):
    await service.delete(permission_id)

    return success_response(
        code=200,
        message="Permission deleted successfully",
        data=None,
    )