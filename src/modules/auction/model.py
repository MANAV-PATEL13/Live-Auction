from datetime import datetime, timezone

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, IndexModel

from src.common.audit import AuditMixin


class Auction(Document, AuditMixin):

    session_id : PydanticObjectId

    user_id : PydanticObjectId

    base_price : int = Field(ge=0)

    status : str

    current_bid : int = Field(default=0,ge=0)
    current_team_id : PydanticObjectId | None = None

    started_at : datetime | None = None
    ended_at : datetime | None = None

    class Settings:
        name = "auctions"

        indexes = [
            IndexModel(
                [("session_id", ASCENDING)],
                name = "idx_auction_session",
            ),
            IndexModel(
                [("user_id", ASCENDING)],
                name = "idx_auction_user",
            ),
            IndexModel(
                [("status", ASCENDING)],
                name = "idx_auction_status"
            ),
            IndexModel(
                [("created_at", ASCENDING)],
                name = "idx_auction_created"
            )
        ]

        