from datetime import datetime
from pydantic import BaseModel, Field


class TeamCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    code: str = Field(min_length=1, max_length=30)
    image_url: str | None = None
    captain_id: str | None = None
    vice_captain_id: str | None = None
    initial_balance: int = Field(default=6250, ge=0)
    is_active: bool = True


class TeamUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    code: str | None = Field(default=None, min_length=1, max_length=30)
    image_url: str | None = None
    captain_id: str | None = None
    vice_captain_id: str | None = None
    is_active: bool | None = None


class TeamResponse(BaseModel):
    id: str
    name: str
    code: str
    image_url: str | None = None
    captain_id: str | None = None
    vice_captain_id: str | None = None
    initial_balance: int
    balance: int
    is_active: bool
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime
    updated_at: datetime


class SetCaptainRequest(BaseModel):
    captain_id: str


class SetViceCaptainRequest(BaseModel):
    vice_captain_id: str


class WalletAdjustmentRequest(BaseModel):
    amount: int  # can be positive (credit) or negative (debit)
    description: str = Field(min_length=3, max_length=255)


class TeamWalletTransactionResponse(BaseModel):
    id: str
    team_id: str
    transaction_type: str
    amount: int
    balance_before: int
    balance_after: int
    user_id: str | None = None
    description: str | None = None
    created_by: str | None = None
    created_at: datetime


class TeamWalletResponse(BaseModel):
    team_id: str
    team_name: str
    initial_balance: int
    balance: int
    total_spent: int
    total_refunded: int
    active_players_count: int
    total_transactions: int
