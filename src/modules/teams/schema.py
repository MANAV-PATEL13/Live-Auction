from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class TeamCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    code: str = Field(min_length=1, max_length=30)
    image_url: str | None = None
    is_active: bool = True


class TeamUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    code: str | None = Field(default=None, min_length=1, max_length=30)
    image_url: str | None = None
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

    @field_validator("id", "captain_id", "vice_captain_id", "created_by", "updated_by", mode="before")
    @classmethod
    def convert_objectid(cls, v):
        if v is not None:
            return str(v)
        return v


class TeamLeadershipUpdate(BaseModel):
    captain_id: str | None = None
    vice_captain_id: str | None = None
    vice_captain_price: int = Field(default=0, ge=0)


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

    @field_validator("id", "team_id", "user_id", "created_by", mode="before")
    @classmethod
    def convert_objectid(cls, v):
        if v is not None:
            return str(v)
        return v


class TeamWalletResponse(BaseModel):
    team_id: str
    team_name: str
    initial_balance: int
    balance: int
    total_spent: int
    total_refunded: int
    total_transactions: int

    @field_validator("team_id", mode="before")
    @classmethod
    def convert_objectid(cls, v):
        if v is not None:
            return str(v)
        return v


class TeamMemberAssignmentRequest(BaseModel):
    price: int = Field(ge=0)


# Backward compatibility alias
TeamMemberAssign = TeamMemberAssignmentRequest


class TeamMemberTransferRequest(BaseModel):
    source_team_id: str
    price: int | None = Field(default=None, ge=0)


from src.modules.users.schema import UserResponse

class TeamMembersResponse(BaseModel):
    team_id: str
    team_name: str
    members: list[UserResponse]

    @field_validator("team_id", mode="before")
    @classmethod
    def convert_objectid(cls, v):
        if v is not None:
            return str(v)
        return v
