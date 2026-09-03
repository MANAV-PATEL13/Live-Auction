from pydantic import BaseModel, Field

from src.modules.registration.model import SportLevel, TshirtSize


class RegistrationCreate(BaseModel):

    tshirt_size: TshirtSize

    cricket: SportLevel
    volleyball: SportLevel
    kabaddi: SportLevel
    kho_kho: SportLevel
    foosball: SportLevel
    frisbee: SportLevel
    dodge_ball: SportLevel
    chess: SportLevel
    carrom: SportLevel
    tennis: SportLevel

    single_talent: str | None = Field(
        default=None,
        max_length=500,
    )

    group_talent_contribution: int = Field(
        ge=0,
        le=100,
    )

    qna_contribution : int = Field(
            default=None,
            ge=0,
            le=100
    )


class RegistrationUpdate(BaseModel):

    tshirt_size: TshirtSize | None = None

    cricket: SportLevel | None = None
    volleyball: SportLevel | None = None
    kabaddi: SportLevel | None = None
    kho_kho: SportLevel | None = None
    foosball: SportLevel | None = None
    frisbee: SportLevel | None = None
    dodge_ball: SportLevel | None = None
    chess: SportLevel | None = None
    carrom: SportLevel | None = None
    tennis: SportLevel | None = None

    single_talent: str | None = Field(
        default=None,
        max_length=500,
    )

    group_talent_contribution: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    qna_contribution : int | None = Field(
            default=None,
            ge=0,
            le=100
    )