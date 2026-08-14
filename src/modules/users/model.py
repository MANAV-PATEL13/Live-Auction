from datetime import datetime, timezone

from beanie import Document
from pydantic import EmailStr, Field


class User(Document):

    name : str
    first_name : str
    middle_name : str | None = None
    last_name : str

    group_ids : list[str] = Field(
        default_factory=list
    )

    roll_no : str | None = None

    email : EmailStr
    mobile : str | None = None

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