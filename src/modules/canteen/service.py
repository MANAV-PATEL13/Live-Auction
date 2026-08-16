from beanie import PydanticObjectId

from src.modules.canteen.model import MenuItem
from src.modules.canteen.repository import MenuItemRepository
from src.modules.canteen.schema import MenuItemCreate, MenuItemUpdate
from src.modules.users.model import User



class MenuItemService:

    def __init__(
        self,
        repository: MenuItemRepository = None,
    ):
        self.repository = repository or MenuItemRepository()

    async def create(
        self,
        data: MenuItemCreate,
        current_user: User,
    ) -> MenuItem:

        item = MenuItem(
            **data.model_dump(),
            created_by=current_user.id,
            updated_by=current_user.id,
        )

        return await self.repository.create(item)

    async def get_by_id(
        self,
        item_id: PydanticObjectId,
    ) -> MenuItem:

        item = await self.repository.get_by_id(item_id)

        if not item:
            # use your existing NotFoundException
            raise Exception("Menu item not found")

        return item

    async def get_all(
            self,
            current_user : User
        ) -> list[MenuItem]:

        from src.modules.auth.dependencies import check_user_permission

        include_hidden = False
        if current_user.is_superuser or await check_user_permission(current_user, "canteen:item:update"):
            include_hidden = True

        return await self.repository.get_all(include_hidden=include_hidden)

    async def update(
        self,
        item_id: PydanticObjectId,
        data: MenuItemUpdate,
        current_user: User,
    ) -> MenuItem:

        item = await self.get_by_id(item_id)

        update_data = data.model_dump(
            exclude_unset=True
        )

        for field, value in update_data.items():
            setattr(item, field, value)

        item.mark_updated(current_user.id)

        return await self.repository.update(item)

    async def delete(
        self,
        item_id: PydanticObjectId,
    ) -> None:

        item = await self.get_by_id(item_id)

        await self.repository.delete(item)