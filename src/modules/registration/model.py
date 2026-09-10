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
    apc_year : int
    tshirt_size : TshirtSize

    # sports
    cricket : SportLevel = SportLevel.NO
    volleyball : SportLevel = SportLevel.NO
    kabaddi : SportLevel = SportLevel.NO
    kho_kho : SportLevel = SportLevel.NO
    foosball : SportLevel = SportLevel.NO
    frisbee : SportLevel = SportLevel.NO
    dodge_ball : SportLevel = SportLevel.NO
    chess : SportLevel = SportLevel.NO
    carrom : SportLevel = SportLevel.NO
    tennis : SportLevel = SportLevel.NO

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
                [("apc_year",ASCENDING)],
                name="idx_registration_apc_yser",
            ),
            IndexModel(
                [("user_id",ASCENDING),("apc_year",ASCENDING)],
                unique=True,
                name="uq_registration_user_year",
            ),
        ]