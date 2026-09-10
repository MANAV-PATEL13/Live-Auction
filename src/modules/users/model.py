from datetime import datetime, timezone

from beanie import Document, PydanticObjectId
from pydantic import EmailStr, Field
from pymongo import ASCENDING, IndexModel

class User(Document):

    name : str

    first_name : str
    middle_name : str | None = None
    last_name : str

    group_ids : list[str] = Field(
        default_factory=list
    )

    team_id: PydanticObjectId | None = None
    team_price: int = Field(
        default=0,
        ge=0,
    )

    is_registered : bool = False
    base_price : int = Field(default=0, ge=0)

    roll_no : str | None = None
    email : EmailStr
    mobile : str | None = None
    image_url : str | None = None

    password_hash : str

    is_active : bool = True
    is_allowed : bool = True
    is_superuser : bool = False

    created_at : datetime = Field(
        default_factory = lambda: datetime.now(timezone.utc)
    )

    updated_at : datetime = Field(
        default_factory = lambda: datetime.now(timezone.utc)
    )


    class Settings:
        name = "users"

        indexes = [
            IndexModel(
                [("email", ASCENDING)],
                unique=True,
                name="uq_user_email",
            ),
            IndexModel(
                [("mobile", ASCENDING)],
                name="idx_user_mobile",
            ),
            IndexModel(
                [("team_id", ASCENDING)],
                name="idx_user_team_id",
            ),
            IndexModel(
                [("is_registered", ASCENDING)],
                name="idx_user_is_registered",
            ),
            IndexModel(
                [("roll_no", ASCENDING)],
                name="idx_user_roll_no",
            ),
        ]