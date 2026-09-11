from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import StreamingResponse

import io

from src.modules.users.schema import UserGroupsUpdate, UserUpdate, ChangePasswordRequest
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
            "image_url": current_user.image_url,
            "is_active": current_user.is_active,
            "is_allowed": current_user.is_allowed,
            "is_superuser": current_user.is_superuser,
        },
    )


@router.post("/import")
async def import_users(
    file: UploadFile = File(...),
    current_user : User = Depends(
        require_permission("user:create")
    )
):
    
    if not file.filename:
        return success_response(
            code=400,
            message="CSV file is required",
            data=None
        )

    if not file.filename.lower().endswith(".csv"):
        return success_response(
            code=400,
            message="Only CSV files are allowed",
            data=None
        )

    content = await file.read()

    result = await service.import_csv(content)

    return success_response(
        code=200,
        message="User CSV import completed",
        data=result
    )


@router.get("/import/template")
async def download_user_import_template(
    current_user: User = Depends(
        require_permission("user:create")
    ),
):
    csv_content = (
        "first_name,middle_name,last_name,roll_no,email,mobile,image_url\n"
        "Manav,,Patel,101,manav@example.com,9876543210,https://example.com/photo.jpg\n"
    )

    return StreamingResponse(
        io.BytesIO(
            csv_content.encode("utf-8")
        ),
        media_type="text/csv",
        headers={
            "Content-Disposition":
                'attachment; filename="users_import_template.csv"'
        },
    )


@router.get("/export")
async def export_users(
    current_user : User = Depends(
        require_permission("user:view")
    ),
):

    return await service.export_csv()


@router.get("/{user_id}/team")
async def get_user_team(
    user_id: str,
    current_user: User = Depends(
        require_permission("team:view")
    ),
):
    team = await service.get_user_team(user_id)

    data = None

    if team:
        data = {
            "id": str(team.id),
            "name": team.name,
            "code": team.code,
            "balance": team.balance,
        }

    return success_response(
        code=200,
        message="User team fetched successfully",
        data=data,
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


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    data: UserUpdate,
    current_user: User = Depends(
        require_permission("user:update")
    ),
):
    user = await service.update(
        user_id,
        data,
    )

    return success_response(
        code=200,
        message="User updated successfully",
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


@router.put("/me/password")
async def change_own_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Authenticated user changes their own password.
    Requires verifying the current password first.
    """
    await service.change_password(
        str(current_user.id),
        data,
    )

    return success_response(
        code=200,
        message="Password changed successfully",
        data=None,
    )


@router.put("/{user_id}/password")
async def reset_user_password(
    user_id: str,
    current_user: User = Depends(
        require_permission("user:update")
    ),
):
    """
    Admin resets a user's password to the default (roll_no@321).
    Requires 'user:update' permission.
    """
    await service.reset_password(user_id)

    return success_response(
        code=200,
        message="Password reset to default successfully",
        data=None,
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

@router.post("/base-price/import")
async def import_base_prices(
    file: UploadFile = File(...),
    current_user: User = Depends(
        require_permission("user:update")
    ),
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

    result = await service.import_base_prices(
        content
    )

    return success_response(
        code=200,
        message="Base price CSV import completed",
        data=result,
    )

@router.get("/base-price/import/template")
async def download_base_price_template(
    current_user: User = Depends(
        require_permission("user:update")
    ),
):
    csv_content = (
        "roll_no,base_price\n"
        "101,500\n"
    )

    return StreamingResponse(
        io.BytesIO(
            csv_content.encode("utf-8")
        ),
        media_type="text/csv",
        headers={
            "Content-Disposition":
                'attachment; filename="base_price_import_template.csv"'
        },
    )