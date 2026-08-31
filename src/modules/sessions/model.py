from datetime import datetime, timezone

from beanie import Document, PydanticObjectId
from pydantic import Field


class Session(Document):

    user_id : PydanticObjectId

    # Device information
    device_id : str
    device_name : str | None = None
    platform : str | None = None

    # Session
    is_active : bool = True

    # login information
    login_at : datetime = Field(
        default_factory= lambda: datetime.now(timezone.utc)
    )

    # session logout
    logout_at : datetime | None = None
    invalidated_at : datetime | None = None
    invalidated_reason : str | None = None


    class Settings:
        name = "sessions"