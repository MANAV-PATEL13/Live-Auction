from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):

    first_name : str = Field(min_length=1)
    middle_name : str | None = None
    last_name : str = Field(min_length=1)

    roll_no : str | None = None

    email : EmailStr
    mobile : str | None = None
    image_url : str | None = None

    password : str = Field(min_length=6)


class UserResponse(BaseModel):
    id: str
    name: str
    first_name: str
    middle_name: str | None = None
    last_name: str

    roll_no: str | None = None
    email: EmailStr
    mobile: str | None = None
    image_url: str | None = None

    team_id: str | None = None
    team_price: int = 0

    base_price: int = 0
    is_registered: bool = False

    is_active: bool
    is_allowed: bool
    is_superuser: bool

class UserUpdate(BaseModel):

    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None

    base_price : int | None = Field(
        default=None,
        ge=0,
    )

    group_ids: list[str] | None = None

    roll_no: str | None = None
    email: EmailStr | None = None
    mobile: str | None = None
    image_url: str | None = None

    is_registered: bool | None = None
    is_active: bool | None = None
    is_allowed: bool | None = None

class UserGroupsUpdate(BaseModel):
    group_ids : list[str]


class ChangePasswordRequest(BaseModel):
    current_password : str = Field(min_length=1)
    new_password : str = Field(min_length=6)
