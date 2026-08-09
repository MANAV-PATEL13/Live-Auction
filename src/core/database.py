from motor.motor_asyncio import AsyncIOMotorClient

from src.core.config import settings

client = AsyncIOMotorClient(
    settings.MONGO_URL
)

database = client[
    settings.DATABASE_NAME
]