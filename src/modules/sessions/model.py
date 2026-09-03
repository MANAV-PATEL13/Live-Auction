from datetime import datetime, timezone

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel


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

        indexes = [
            IndexModel(
                [("user_id", ASCENDING)],
                name="idx_session_user_id",
            ),
            IndexModel(
                [("is_active", ASCENDING)],
                name="idx_session_is_active",
            ),
            IndexModel(
                [("login_at", ASCENDING)],
                name="idx_session_login_at",
            ),
            IndexModel(
                [("user_id", ASCENDING), ("is_active", ASCENDING)],
                name="idx_session_user_is_active",
            ),
            IndexModel(
                [("user_id", ASCENDING), ("login_at", DESCENDING)],
                name="idx_session_user_login_at",
            ),
        ]