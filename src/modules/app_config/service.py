from src.modules.app_config.model import AppConfig
from src.modules.app_config.schema import AppConfigUpdate, AppConfigCreate
from src.modules.app_config.repository import AppConfigRepository
from src.modules.users.model import User
from src.common.exceptions import NotFoundException


class AppConfigService:

    def __init__(self, repository : AppConfigRepository):

        self.repository = repository

    async def get(self) -> AppConfig:

        config = await self.repository.get()

        if not config:
            raise NotFoundException(
                "App configuration not found"
            )

        return config

    async def create(
            self,
            data : AppConfigCreate,
            current_user: User
        ) -> AppConfig:

            existing = await self.repository.get()

            if existing:
                 return existing

            config = AppConfig(
                 **data.model_dump(exclude_unset=True),
                 created_by=current_user.id,
                 updated_by=current_user.id,
            )

            return await self.repository.create(config)

    async def update(
            self,
            data : AppConfigUpdate,
            current_user : User
    ) -> AppConfig:

        config = await self.get()

        update_data = data.model_dump(
             exclude_unset=True
        )

        for field, value in update_data.items():
            setattr(config, field, value)

        config.mark_updated(current_user.id)

        return await self.repository.update(
            config,
            update_data
        )