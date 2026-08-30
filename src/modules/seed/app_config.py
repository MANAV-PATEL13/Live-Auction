import asyncio

from src.core.database import init_database, client
from src.modules.app_config.model import AppConfig


async def seed_app_config():

    await init_database()

    existing = await AppConfig.find_one()

    if existing:
        print("AppConfig already exists")
        return

    config = AppConfig(
        maintenance_mode=False,
        maintenance_message=None,
        minimum_version="1.0.0",
        latest_version="1.0.0",
        update_message=None,
        android_store_url=None,
        created_by=None,
        updated_by=None,
    )

    await config.insert()

    print("AppConfig created")


if __name__ == "__main__":
    asyncio.run(seed_app_config())