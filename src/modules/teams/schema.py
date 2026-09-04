from pydantic import BaseModel, Field
from datetime import datetime

class TeamCreate(BaseModel):

    name : str = Field(min_length=2, max_length=100)
    code : str = Field(min_length=1, max_length=30)
    image_url : str | None = None

    captain_id : str | None = None
    vice_captain_id : str | None = None
    
    is_active : bool = True

class TeamUpdate(BaseModel):

    name : str | None = Field(default=None, min_length=2, max_length=100)
    code : str | None = Field(default=None, min_length=1, max_length=30)
    image_url : str | None = None
    
    captain_id : str | None = None
    vice_captain_id : str | None = None

    is_active : bool | None = None


class TeamResponse(BaseModel):

    id : str

    name : str
    code : str
    image_url : str | None = None

    captain_id : str | None = None
    vice_captain_id : str | None = None

    pushp_balance : int

    is_active : bool

    created_by : str
    updated_by : str

    created_at : datetime
    updated_at : datetime


