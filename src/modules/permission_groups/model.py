from beanie import Document
from pydantic import Field


class PermissionGroup(Document):

    name: str
    description : str | None = None

    permission_ids: list[str] = Field(
        default_factory=list
    )

    is_active: bool = True


    class Settings:
        name = "permission_groups"