from datetime import datetime
from pydantic import BaseModel, Field


class TeamAssignmentCreate(BaseModel):
    user_id: str
    team_id: str
    price: int = Field(default=0, ge=0)


class TeamTransferRequest(BaseModel):
    new_team_id: str
    price: int | None = Field(default=None, ge=0)


class TeamAssignmentResponse(BaseModel):
    id: str
    user_id: str
    team_id: str
    price: int

    assigned_at: datetime
    assigned_by: str

    removed_at: datetime | None = None
    removed_by: str | None = None

    is_current: bool


class TeamMemberResponse(BaseModel):
    user_id: str
    team_id: str
    price: int
    assigned_at: datetime