
from beanie import Document

from src.common.audit import AuditMixin

class AppConfig(Document, AuditMixin):

    maintenance_mode : bool = False
    maintenance_message : str | None = None

    minimum_version : str
    latest_version : str

    update_message : str | None = None

    android_store_url : str | None=None

    registration_open: bool = False

    class Settings:
        name = "app_config"