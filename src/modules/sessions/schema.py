from datetime import datetime

from beanie import PydanticObjectId
from pydantic import BaseModel


class SessionResponse(BaseModel):

    id : PydanticObjectId

    user_id : PydanticObjectId

    device_id : str
    device_name : str | None = None
    platform : str | None = None

    is_active : bool

    login_at : datetime

    logout_at : datetime | None = None
    invalidated_at : datetime | None = None
    invalidated_reason : str | None = None