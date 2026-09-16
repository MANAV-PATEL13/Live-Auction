from datetime import datetime, timezone
from typing import Any
from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import DESCENDING, IndexModel


class AuctionActivityLog(Document):
    session_id: PydanticObjectId | None = None
    auction_id: PydanticObjectId | None = None
    type: str  # "BID", "SOLD", "UNSOLD", "SESSION_STATUS", "BID_ROLLBACK", "PLAYER_START", "BIDDING_TOGGLE", "PLAYER_DISPLAY", "PLAYER_STANDBY"
    title: str
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    class Settings:
        name = "auction_activity_logs"
        indexes = [
            IndexModel(
                [("created_at", DESCENDING)],
                name="idx_activity_created_desc",
            ),
            IndexModel(
                [("session_id", DESCENDING), ("created_at", DESCENDING)],
                name="idx_activity_session_created",
            ),
            IndexModel(
                [("type", DESCENDING)],
                name="idx_activity_type",
            ),
        ]
