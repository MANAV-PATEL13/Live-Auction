from beanie import PydanticObjectId
from fastapi import Depends, APIRouter

from src.common.utils import success_response
from src.modules.canteen.service import MenuItemService
from src.modules.auth.dependencies import require_permission
from src.modules.canteen.schema import MenuItemCreate, MenuItemUpdate
from src.modules.users.model import User

router = APIRouter(
    prefix="/canteen",
    tags=["canteen"]
)



menu_service = MenuItemService()

@router.post("")
async def create_menu_item(
    data: MenuItemCreate,
    current_user: User = Depends(
        require_permission("canteen:item:create")
    ),
):
    item = await menu_service.create(
        data=data,
        current_user=current_user,
    )

    return success_response(
        code=201,
        message="Menu item created successfully",
        data=item,
    )

@router.get("")
async def get_menu_items(
    current_user: User = Depends(
        require_permission("canteen:item:view")
    ),
):
    items = await menu_service.get_all(current_user)

    return success_response(
        code=200,
        message="Menu items fetched successfully",
        data=items,
    )

@router.get("/{item_id}")
async def get_menu_item(
    item_id : PydanticObjectId,
    current_user: User = Depends(
        require_permission("canteen:item:view")
    )
):
    item = await menu_service.get_by_id(item_id)

    return success_response(
        code=200,
        message="Menu item fetched successfully",
        data=item,
    )


@router.put("/{item_id}")
async def update_menu_item(
    item_id: PydanticObjectId,
    data: MenuItemUpdate,
    current_user: User = Depends(
        require_permission("canteen:item:update")
    ),
):
    item = await menu_service.update(
        item_id=item_id,
        data=data,
        current_user=current_user,
    )

    return success_response(
        code=200,
        message="Menu item updated successfully",
        data=item,
    )

@router.delete("/{item_id}")
async def delete_menu_item(
    item_id: PydanticObjectId,
    current_user: User = Depends(
        require_permission("canteen:item:delete")
    ),
):
    await menu_service.delete(item_id)

    return success_response(
        code=200,
        message="Menu item deleted successfully",
        data=None,
    )