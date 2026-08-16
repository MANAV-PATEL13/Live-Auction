from pymongo import AsyncMongoClient
from beanie import init_beanie

from src.core.config import settings

# models..
from src.modules.users.model import User
from src.modules.permission_groups.model import PermissionGroup
from src.modules.permissions.model import Permission
from src.modules.canteen.model import MenuItem

client = AsyncMongoClient(
    settings.MONGO_URL
)

database = client[
    settings.DATABASE_NAME
]

async def init_database():

    await init_beanie(
        database= database,
        document_models=[
            User,
            Permission,
            PermissionGroup,
            MenuItem
        ]
    )