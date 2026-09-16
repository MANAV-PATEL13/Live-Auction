from pydantic import BaseModel, Field


class PermissionGroupCreate(BaseModel):

    name: str = Field(
        min_length=2,
        max_length=100,
    )

    description: str | None = None

    permission_ids: list[str] = Field(
        default_factory=list
    )


class PermissionGroupUpdate(BaseModel):

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    description: str | None = None

    permission_ids: list[str] | None = None

    is_active: bool | None = None


class GroupAssignUsersRequest(BaseModel):
    user_ids: list[str] = Field(default_factory=list)