from datetime import datetime, timezone

from beanie import PydanticObjectId
from pydantic import BaseModel, Field


class AuditMixin(BaseModel):
    created_by : PydanticObjectId
    updated_by : PydanticObjectId

    created_at : datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    updated_at : datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def mark_updated(
            self,
            user_id : PydanticObjectId,
    ) -> None:

        self.updated_by = user_id
        self.updated_at = datetime.now(timezone.utc)