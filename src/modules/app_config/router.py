from fastapi import APIRouter, Depends
from src.common.response import ResponseModel
from src.modules.app_config.schema import AppConfigUpdate, AppConfigPublicResponse, AppConfigResponse

from src.modules.app_config.service import AppConfigService
from src.modules.app_config.repository import AppConfigRepository

from src.modules.users.model import User
from src.modules.auth.dependencies import get_current_user

from src.common.utils import success_response
from src.modules.auth.dependencies import require_permission


router = APIRouter(
    prefix="/app-config",
    tags=["App Config"],
)


def get_service() -> AppConfigService:
    return AppConfigService(
        AppConfigRepository()
    )


@router.get(
    "",
    response_model=ResponseModel[AppConfigResponse],
)
async def get_app_config(
    service: AppConfigService = Depends(get_service),
):
    config = await service.get()

    return success_response(
        code=200,
        message="App configuration fetched successfully",
        data=config,
    )


@router.get(
    "/public",
    response_model=ResponseModel[AppConfigPublicResponse],
)
async def get_public_app_config(
    service: AppConfigService = Depends(get_service),
):
    config = await service.get()

    return success_response(
        code=200,
        message="App configuration fetched successfully",
        data=config,
    )


@router.post(
    "",
    response_model=ResponseModel[AppConfigResponse],
)
async def create_app_config(
    data: AppConfigUpdate,
    current_user: User = Depends(
        require_permission("appconfig:create")
    ),
    service: AppConfigService = Depends(get_service),
):
    config = await service.create(
        data,
        current_user,
    )

    return success_response(
        code=201,
        message="App configuration created successfully",
        data=config,
    )


@router.put(
    "",
    response_model=ResponseModel[AppConfigResponse],
)
async def update_app_config(
    data: AppConfigUpdate,
    current_user: User = Depends(
        require_permission("appconfig:update")
    ),
    service: AppConfigService = Depends(get_service),
):
    config = await service.update(
        data,
        current_user,
    )

    return success_response(
        code=200,
        message="App configuration updated successfully",
        data=config,
    )