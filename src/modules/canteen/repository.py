from beanie import PydanticObjectId

from src.modules.canteen.model import MenuItem

class MenuItemRepository:

    async def create(
            self,
            item : MenuItem
    ) -> MenuItem:

        await item.insert()

        return item


    async def get_by_id(
            self,
            item_id : PydanticObjectId
    ) -> MenuItem | None:

        return await MenuItem.get(item_id)


    async def get_all(
            self,
            include_hidden : bool = False
    ) -> list[MenuItem]:

        if include_hidden:
            return await MenuItem.find_all().to_list()

        return await MenuItem.find(
            MenuItem.is_show == True
        ).to_list()


    async def update(
            self,
            item : MenuItem,
    ) -> MenuItem:

        await item.save()


    async def delete(
            self,
            item : MenuItem,
    )-> None:

        await item.delete()