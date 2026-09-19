from beanie import PydanticObjectId

from src.modules.permissions.model import Permission


class PermissionRepository:

    async def create(
        self,
        permission: Permission,
    ) -> Permission:
        await permission.insert()
        return permission

    async def get_by_id(
        self,
        permission_id: str,
    ) -> Permission | None:

        if not PydanticObjectId.is_valid(permission_id):
            return None

        return await Permission.get(
            PydanticObjectId(permission_id)
        )

    async def get_by_code(
        self,
        code: str,
    ) -> Permission | None:

        return await Permission.find_one(
            Permission.code == code
        )

    async def get_all(
        self,
    ) -> list[Permission]:

        return await Permission.find_all().to_list()

    async def update(
        self,
        permission: Permission,
    ) -> Permission:

        await permission.save()

        return permission

    async def delete(
        self,
        permission: Permission,
    ) -> None:

        await permission.delete()