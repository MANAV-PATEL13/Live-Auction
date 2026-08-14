from pydantic import BaseModel, Field


class PermissionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    code: str = Field(min_length=2, max_length=100)
    description: str | None = None


class PermissionResponse(BaseModel):
    name : str
    code : str
    description : str


class PermissionUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )
    code: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )
    description: str | None = None
    is_active: bool | None = None