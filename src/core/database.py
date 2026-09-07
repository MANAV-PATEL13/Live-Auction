from pymongo import AsyncMongoClient
from beanie import init_beanie

from src.core.config import settings

# models..
from src.modules.users.model import User
from src.modules.permission_groups.model import PermissionGroup
from src.modules.permissions.model import Permission
from src.modules.canteen.model import MenuItem
from src.modules.teams.model import Team
from src.modules.app_config.model import AppConfig
from src.modules.sessions.model import Session
from src.modules.registration.model import Registration
from src.modules.team_assignments.model import TeamAssignment
from src.modules.teams.wallet_model import TeamWalletTransaction

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
            MenuItem,
            Team,
            AppConfig,
            Session,
            Registration,
            TeamAssignment,
            TeamWalletTransaction,
        ]
    )