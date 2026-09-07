from datetime import datetime, timezone

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, IndexModel


class TeamAssignment(Document):
    user_id: PydanticObjectId
    team_id: PydanticObjectId
    price: int = Field(default=0, ge=0)

    assigned_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    assigned_by: PydanticObjectId

    removed_at: datetime | None = None
    removed_by: PydanticObjectId | None = None

    is_current: bool = True

    class Settings:
        name = "team_assignments"

        indexes = [
            IndexModel(
                [
                    ("user_id", ASCENDING),
                    ("is_current", ASCENDING),
                ],
                name="idx_assignment_user_current",
            ),
            IndexModel(
                [
                    ("team_id", ASCENDING),
                    ("is_current", ASCENDING),
                ],
                name="idx_assignment_team_current",
            ),
            IndexModel(
                [("user_id", ASCENDING)],
                name="idx_assignment_user",
            ),
            IndexModel(
                [("team_id", ASCENDING)],
                name="idx_assignment_team",
            ),
        ]