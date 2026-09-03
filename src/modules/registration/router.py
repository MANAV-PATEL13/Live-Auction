from fastapi import APIRouter, Depends
from beanie import PydanticObjectId

from src.common.utils import success_response
from src.modules.auth.dependencies import get_current_user, require_permission

from src.modules.registration.schema import RegistrationUpdate, RegistrationCreate

from src.modules.registration.service import RegistrationService
from src.modules.registration.repository import RegistrationRepository

from src.modules.users.model import User

router = APIRouter(
    prefix="/registration",
    tags=["Registration"]
)

repository = RegistrationRepository()
service = RegistrationService(repository)


@router.post("")
async def create_registration(
    data : RegistrationCreate,
    current_user : User = Depends(get_current_user),
):

    registration = await service.create(
        data,
        current_user
    )

    return success_response(
        code=201,
        message="Registration completed successfully",
        data=registration,
    )


@router.get("/me")
async def get_my_registration(
    current_user : User = Depends(get_current_user),
):

    registration = await service.get_by_user_id(
        current_user.id
    )

    return success_response(
        code=200,
        message="Registration fetched successfully",
        data=registration
    )


@router.get("/all")
async def get_all_registration(
    current_user : User = Depends(
        require_permission("registration:view")
    ),
):

    registrations = await service.get_all()

    return success_response(
        code=200,
        message="Registration fetched successfully",
        data=registrations
    )


@router.get("/{registration_id}")
async def get_registration(
    registration_id : PydanticObjectId,
    current_user : User = Depends(
        require_permission("registration:view")
    )
):
    registration = await service.get_by_id(
        registration_id
    )

    return success_response(
        code=200,
        message="Registration fetched successfully",
        data=registration
    )


@router.put("/{registration_id}")
async def update_registration(
    registration_id : PydanticObjectId,
    data : RegistrationUpdate,
    current_user : User = Depends(
        require_permission("registration:update")
    )
):

    registration = await service.update(
        registration_id,
        data,
        current_user,
    )

    return success_response(
        code=200,
        message="Registration updated successfully",
        data=registration
    )