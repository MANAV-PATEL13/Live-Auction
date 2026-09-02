from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING

from src.common.audit import AuditMixin

class Team( AuditMixin, Document):

    name : str = Field(min_length=2, max_length=100)
    code : str = Field(min_length=1, max_length=30)
    image_url : str | None = None

    captain_id : PydanticObjectId | None = None
    vice_captain_id : PydanticObjectId | None = None
    
    is_active : bool = True

    class Settings:
        name = "teams"

        indexes = [
            {
                "keys" : [
                    ("code",ASCENDING),
                ],
                "unique" : True,
                "name" : "uq_team_code"
            },

            [
                ("is_active",ASCENDING),
            ],
            [
                ("captain_id",ASCENDING),
            ],
            [
                ("vice_captain_id",ASCENDING),
            ],
        ]