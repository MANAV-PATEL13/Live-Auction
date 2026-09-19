from beanie import Document
from pydantic import Field

from src.common.audit import AuditMixin


class Permission(AuditMixin, Document):

    name: str
    code: str
    description: str | None = None
    is_active: bool = True

    class Settings:
        name = "permissions"