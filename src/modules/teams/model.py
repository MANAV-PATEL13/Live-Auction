from beanie import Document, PydanticObjectId
from pydantic import Field

from src.common.audit import AuditMixin

class Team( AuditMixin, Document):

    name : str = Field(min_length=2)
    code : str = Field(min_length=1)
    image_url : str | None = None

    captain_id : PydanticObjectId | None = None
    vice_captain_id : PydanticObjectId | None = None
    

    is_active : bool = True

    class Settings:
        name = "teams"