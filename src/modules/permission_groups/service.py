from src.common.exceptions import AppException

from src.modules.permission_groups.model import PermissionGroup
from src.modules.permission_groups.repository import (
    PermissionGroupRepository,
)
from src.modules.permission_groups.schema import (
    PermissionGroupCreate,
    PermissionGroupUpdate,
)
from src.modules.permissions.repository import (
    PermissionRepository,
)
from src.modules.users.model import User


class PermissionGroupService:

    def __init__(self):

        self.repo = PermissionGroupRepository()
        self.permission_repo = PermissionRepository()

    async def _validate_permissions(
        self,
        permission_ids: list[str],
    ) -> None:

        for permission_id in permission_ids:

            permission = await self.permission_repo.get_by_id(
                permission_id
            )

            if not permission:

                raise AppException(
                    message=f"Permission not found: {permission_id}",
                    code=404,
                )

    async def create(
        self,
        data: PermissionGroupCreate,
        current_user: User,
    ) -> PermissionGroup:

        existing = await self.repo.get_by_name(
            data.name
        )

        if existing:

            raise AppException(
                message="Permission group already exists",
                code=409,
            )

        await self._validate_permissions(
            data.permission_ids
        )

        group = PermissionGroup(
            name=data.name,
            description=data.description,
            permission_ids=data.permission_ids,
            created_by=current_user.id,
            updated_by=current_user.id,
        )

        return await self.repo.create(group)

    async def get_by_id(
        self,
        group_id: str,
    ) -> PermissionGroup:

        group = await self.repo.get_by_id(
            group_id
        )

        if not group:

            raise AppException(
                message="Permission group not found",
                code=404,
            )

        return group

    async def get_all(
        self,
    ) -> list[PermissionGroup]:

        return await self.repo.get_all()

    async def update(
        self,
        group_id: str,
        data: PermissionGroupUpdate,
        current_user: User,
    ) -> PermissionGroup:

        group = await self.get_by_id(group_id)

        update_data = data.model_dump(
            exclude_unset=True
        )

        if "name" in update_data:

            existing = await self.repo.get_by_name(
                update_data["name"]
            )

            if (
                existing
                and str(existing.id) != group_id
            ):

                raise AppException(
                    message="Permission group already exists",
                    code=409,
                )

        if "permission_ids" in update_data:

            await self._validate_permissions(
                update_data["permission_ids"]
            )

        for field, value in update_data.items():
            setattr(group, field, value)

        group.mark_updated(current_user.id)

        return await self.repo.update(group)

    async def delete(
        self,
        group_id: str,
    ) -> None:

        group = await self.get_by_id(group_id)

        await self.repo.delete(group)