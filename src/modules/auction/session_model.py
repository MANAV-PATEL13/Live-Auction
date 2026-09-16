from datetime import datetime, timezone

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, IndexModel

from src.common.audit import AuditMixin


class AuctionSession(Document, AuditMixin):
    status : str

    sort_by : str = "base_price"
    sort_direction : str = "asc"

    remaining_queue : list[PydanticObjectId] = Field(default_factory=list)

    unsold_queue : list[PydanticObjectId] = Field(default_factory=list)

    current_user_id : PydanticObjectId | None = None
    current_auction_id : PydanticObjectId | None = None

    started_at : datetime | None = None
    paused_at : datetime | None = None
    ended_at : datetime | None = None

    class Settings:
        name = "auction_sessions"

        indexes = [
            IndexModel(
                [("status", ASCENDING)],
                name="idx_auction_session_status",
            ),
            IndexModel(
                [("created_at", ASCENDING)],
                name="idx_auction_session_created",
            ),
        ]