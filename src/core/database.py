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
from src.modules.teams.wallet_model import TeamWalletTransaction
from src.modules.team_assignments.model import TeamAssignment
from src.modules.auction.model import Auction
from src.modules.auction.session_model import AuctionSession
from src.modules.auction.bid_model import AuctionBid
from src.modules.auction.activity_log_model import AuctionActivityLog

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
            TeamWalletTransaction,
            TeamAssignment,
            Auction,
            AuctionSession,
            AuctionBid,
            AuctionActivityLog,
        ]
    )