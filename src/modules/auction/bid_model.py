from datetime import datetime, timezone

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, IndexModel

class AuctionBid(Document):
    auction_id : PydanticObjectId

    team_id : PydanticObjectId | None = None
    user_id : PydanticObjectId

    amount : int = Field(gt=0)

    created_at : datetime = Field(
        default_factory= lambda: datetime.now(timezone.utc)
    )

    is_rolled_back: bool = False
    rolled_back_at: datetime | None = None
    rolled_back_by: PydanticObjectId | None = None

    class Settings:
        name = "auction_bids"

        indexes = [
            IndexModel(
                [("auction_id", ASCENDING), ("created_at", ASCENDING)],
                name = "idx_bid_auction_created",
            ),
            IndexModel(
                [("team_id", ASCENDING)],
                name="idx_bid_team",
            ),
            
        ]