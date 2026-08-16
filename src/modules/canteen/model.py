from beanie import Document, PydanticObjectId

from src.common.audit import AuditMixin


class MenuItem(AuditMixin,Document):

    name : str
    price : float
    image_url : str | None = None
    description : str | None = None
    is_show : bool = True

    class Settings:
        name = "canteen"