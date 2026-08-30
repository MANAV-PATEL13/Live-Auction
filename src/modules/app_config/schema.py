from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class AppConfigCreate(BaseModel):

    maintenance_mode: bool = False

    maintenance_message: str | None = None

    minimum_version: str = Field(
        min_length=1
    )

    latest_version: str = Field(
        min_length=1
    )

    update_message: str | None = None

    android_store_url: str | None = None

class AppConfigUpdate(BaseModel):

    maintenance_mode: bool | None = None

    maintenance_message: str | None = None

    minimum_version: str | None = Field(
        default=None,
        min_length=1,
    )

    latest_version: str | None = Field(
        default=None,
        min_length=1,
    )

    update_message: str | None = None

    android_store_url: str | None = None


class AppConfigResponse(BaseModel):

    model_config = {"from_attributes": True}

    id: str


    maintenance_mode: bool
    maintenance_message: str | None

    minimum_version: str
    latest_version: str

    update_message: str | None

    android_store_url: str | None

    created_by: str | None = None
    updated_by: str | None = None

    created_at: datetime
    updated_at: datetime

    @field_validator("id", "created_by", "updated_by", mode="before")
    @classmethod
    def convert_objectid(cls, v):
        if v is not None:
            return str(v)
        return v


class AppConfigPublicResponse(BaseModel):

    maintenance_mode: bool
    maintenance_message: str | None

    minimum_version: str
    latest_version: str

    update_message: str | None

    android_store_url: str | None