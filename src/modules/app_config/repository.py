from beanie import PydanticObjectId

from src.modules.app_config.model import AppConfig


class AppConfigRepository:

    async def get(self) -> AppConfig | None:
        return await AppConfig.find_one()


    async def create(
            self,
            config : AppConfig,
    ) -> AppConfig:

        await config.insert()

        return config

    async def update(
            self,
            config : AppConfig,
            data : dict
    ) -> AppConfig:

        for field, value in data.items():
            setattr(config,field,value)

        await config.save()

        return config