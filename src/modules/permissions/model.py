from beanie import Document
from pydantic import Field


class Permission(Document):

    name: str
    code: str
    description: str | None = None
    is_active: bool = True

    class Settings:
        name = "permissions"