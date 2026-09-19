from datetime import datetime
from typing import Literal

from pydantic import BaseModel


SortField = Literal[
    "current_queue",
    "base_price",
    "roll_no",
    "name",
    "created_at",
    "custom_csv",
]

SortDirection = Literal[
    "asc",
    "desc",
]


class AuctionSessionStartRequest(BaseModel):
    sort_by : SortField = "current_queue"
    sort_direction : SortDirection = "asc"


class AuctionSessionResumeRequest(BaseModel):
    sort_by : SortField | None = None
    sort_direction : SortDirection | None = None


class AuctionSessionResponse(BaseModel):
    id : str

    status : str

    sort_by : str
    sort_direction : str

    remaining_count : int
    unsold_count : int
    sold_count : int = 0

    current_user_id : str | None = None
    current_auction_id : str | None = None

    started_at : datetime | None = None
    paused_at : datetime | None = None
    ended_at : datetime | None = None


class ReorderQueueRequest(BaseModel):
    user_ids: list[str]