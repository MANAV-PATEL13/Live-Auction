from datetime import datetime, timezone
from enum import Enum

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, IndexModel

from src.common.audit import AuditMixin

class SportLevel(str, Enum):
    EXPERT = "expert"
    INTERMEDIATE = "intermediate"
    BEGINNER = "beginner"
    NO = "no"


class TshirtSize(str, Enum):
    XS = "XS"
    S = "S"
    M = "M"
    L = "L"
    XL = "XL"
    XXL = "XXL"
    XXXL = "XXXL"

class Registration( Document, AuditMixin):

    user_id : PydanticObjectId

    tshirt_size : TshirtSize

    # sports
    cricket : SportLevel
    volleyball : SportLevel
    kabaddi : SportLevel
    kho_kho : SportLevel
    foosball : SportLevel
    frisbee : SportLevel
    dodge_ball : SportLevel
    chess : SportLevel
    carrom : SportLevel
    tenis : SportLevel

    single_talent : str | None = None
    group_talent_contribution : int = Field(
        ge=0,
        le=100
    )

    qna_contribution : int = Field(
        ge=0,
        le=100
    )


    class Settings:
        name = "registrations"

        indexes = [
            IndexModel(
                [("user_id",ASCENDING)],
                unique=True,
                name="uq_registration_user",
            ),
            IndexModel(
                [("is_completed",ASCENDING)],
                name="idx_registration_completed",
            ),
        ]