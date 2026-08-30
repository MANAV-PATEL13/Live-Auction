from beanie import PydanticObjectId

from src.modules.permission_groups.model import PermissionGroup


class PermissionGroupRepository:

    async def create(
        self,
        group: PermissionGroup,
    ) -> PermissionGroup:

        await group.insert()

        return group

    async def get_by_id(
        self,
        group_id: str,
    ) -> PermissionGroup | None:

        if not PydanticObjectId.is_valid(group_id):
            return None

        return await PermissionGroup.get(
            PydanticObjectId(group_id)
        )

    async def get_by_name(
        self,
        name: str,
    ) -> PermissionGroup | None:

        return await PermissionGroup.find_one(
            PermissionGroup.name == name
        )

    async def get_all(
        self,
    ) -> list[PermissionGroup]:

        return await PermissionGroup.find_all().to_list()

    async def update(
        self,
        group: PermissionGroup,
    ) -> PermissionGroup:

        await group.save()

        return group

    async def delete(
        self,
        group: PermissionGroup,
    ) -> None:

        await group.delete()