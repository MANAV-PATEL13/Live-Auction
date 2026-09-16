from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field


class AuctionCreate(BaseModel):
    user_id : str


class AuctionResponse(BaseModel):

    id : str
    user_id : str
    base_price : int
    base_price_display : str
    status : str
    current_bid : int
    current_bid_display : str
    current_team_id : str | None = None
    started_at : datetime | None = None
    ended_at : datetime | None = None


class PlaceBidRequest(BaseModel):

    team_id : str | None = None
    amount : int = Field(gt=0)


class SellPlayerRequest(BaseModel):

    team_id : str | None = None


class AuctionBidResponse(BaseModel):

    id : str
    auction_id : str
    team_id : str | None = None
    user_id : str
    amount : int
    amount_display : str
    created_at : datetime


class ToggleBiddingRequest(BaseModel):
    enabled: bool | None = None


class AuctionLiveResponse(BaseModel):

    auction_id : str | None = None
    user_id : str | None = None
    base_price : int | None = None
    base_price_display : str | None = None
    current_bid : int | None = None
    current_bid_display : str | None = None
    current_team_id : str | None = None
    status : str | None = None
    timer : int | None = None
    viewer_count : int = 0
    bidding_enabled : bool = True


# ==========================================================
# PUBLIC SCREEN SCHEMAS (NO AUTH REQUIRED)
# ==========================================================

class PublicPlayerInfo(BaseModel):
    id: str
    name: str
    roll_no: str | None = None
    image_url: str | None = None
    base_price: int
    base_price_display: str
    sports: dict[str, str] | None = None
    games: list[str] = Field(default_factory=list)
    experience_years: str | None = None
    critical_situation: list[str] = Field(default_factory=list)
    creative_talent: list[str] = Field(default_factory=list)
    sportsmanship: list[str] = Field(default_factory=list)
    preference: list[str] = Field(default_factory=list)
    questions: dict[str, Any] | None = None


class PublicTeamSummary(BaseModel):
    id: str
    name: str
    code: str
    image_url: str | None = None


class PublicBidItem(BaseModel):
    id: str
    team_id: str
    team_name: str
    team_code: str
    team_image_url: str | None = None
    amount: int
    amount_display: str
    created_at: datetime


class PublicSessionInfo(BaseModel):
    id: str
    status: str
    remaining_count: int
    unsold_count: int
    started_at: datetime | None = None


class PublicAuctionLiveResponse(BaseModel):
    auction_id: str | None = None
    session: PublicSessionInfo | None = None
    player: PublicPlayerInfo | None = None
    current_bid: int | None = None
    current_bid_display: str | None = None
    current_team: PublicTeamSummary | None = None
    status: str | None = None
    timer: int | None = None
    recent_bids: list[PublicBidItem] = []
    viewer_count: int = 0
    bidding_enabled: bool = True


class PublicRosterPlayer(BaseModel):
    id: str
    name: str
    roll_no: str | None = None
    price: int
    price_display: str
    image_url: str | None = None
    mobile: str | None = None
    is_captain: bool = False
    is_vice_captain: bool = False


class PublicTeamRosterResponse(BaseModel):
    id: str
    name: str
    code: str
    image_url: str | None = None
    captain_id: str | None = None
    captain_name: str | None = None
    captain_mobile: str | None = None
    captain_image_url: str | None = None
    vice_captain_id: str | None = None
    vice_captain_name: str | None = None
    vice_captain_mobile: str | None = None
    vice_captain_image_url: str | None = None
    initial_balance: int
    initial_balance_display: str
    balance: int
    balance_display: str
    players_count: int
    players: list[PublicRosterPlayer] = []


class PublicRecentActivityItem(BaseModel):
    auction_id: str
    player_id: str
    player_name: str
    roll_no: str | None = None
    image_url: str | None = None
    base_price: int
    base_price_display: str
    status: str
    final_price: int | None = None
    final_price_display: str | None = None
    winning_team_id: str | None = None
    winning_team_name: str | None = None
    winning_team_code: str | None = None
    ended_at: datetime | None = None


class RollbackBidResponse(BaseModel):
    auction_id: str
    status: str
    current_bid: int
    current_bid_display: str
    current_team_id: str | None = None
    rolled_back_bid_id: str
    rolled_back_amount: int
    rolled_back_amount_display: str


# ==========================================================
# QUICK ADD PLAYER (LIVE AUCTION INJECTION)
# ==========================================================

class QuickAddPlayerRequest(BaseModel):
    first_name: str
    middle_name: str | None = None
    last_name: str
    roll_no: str | None = None
    email: str
    mobile: str | None = None
    image_url: str | None = None
    base_price: int = Field(default=500, ge=0)

    # Registration questionnaire answers
    games: list[str] = Field(default_factory=list)
    experience_years: str | None = None
    critical_situation: list[str] = Field(default_factory=list)
    creative_talent: list[str] = Field(default_factory=list)
    sportsmanship: list[str] = Field(default_factory=list)
    preference: list[str] = Field(default_factory=list)

    # Queue insertion preference: "end" (append at back) or "next" (insert as #1 next up)
    position: Literal["end", "next"] = "end"


class QuickAddPlayerResponse(BaseModel):
    user_id: str
    name: str
    roll_no: str | None = None
    email: str
    base_price: int
    base_price_display: str
    image_url: str | None = None
    is_registered: bool = True
    in_queue: bool = False
    queue_position: str | None = None
    remaining_count: int = 0
    message: str
