from src.common.exceptions import AppException

from src.modules.permissions.model import Permission
from src.modules.permissions.repository import PermissionRepository
from src.modules.permissions.schema import PermissionCreate, PermissionUpdate

class PermissionService:

    def __init__(self):
        self.repo = PermissionRepository()

    async def create(
        self,
        data: PermissionCreate,
    ) -> Permission:

        existing = await self.repo.get_by_code(
            data.code
        )

        if existing:
            raise AppException(
                message="Permission code already exists",
                code=409,
            )

        permission = Permission(
            name=data.name,
            code=data.code,
            description=data.description,
        )

        return await self.repo.create(permission)

    async def get_by_id(
        self,
        permission_id: str,
    ) -> Permission:

        permission = await self.repo.get_by_id(
            permission_id
        )

        if not permission:
            raise AppException(
                message="Permission not found",
                code=404,
            )

        return permission

    async def get_all(self) -> list[Permission]:

        return await self.repo.get_all()

    async def update(
        self,
        permission_id: str,
        data: PermissionUpdate,
    ) -> Permission:

        permission = await self.get_by_id(
            permission_id
        )

        update_data = data.model_dump(
            exclude_unset=True
        )

        if "code" in update_data:

            existing = await self.repo.get_by_code(
                update_data["code"]
            )

            if existing and str(existing.id) != permission_id:
                raise AppException(
                    message="Permission code already exists",
                    code=409,
                )

        return await self.repo.update(
            permission,
            update_data,
        )

    async def delete(
        self,
        permission_id: str,
    ) -> None:

        permission = await self.get_by_id(
            permission_id
        )

        await self.repo.delete(permission)