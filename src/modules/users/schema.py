from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):

    first_name : str = Field(min_length=1)
    middle_name : str | None = None
    last_name : str = Field(min_length=1)

    roll_no : str | None = None

    email : EmailStr
    mobile : str | None = None

    password : str = Field(min_length=6)


class UserResponse(BaseModel):

    id : str

    name : str
    first_name : str
    middle_name : str | None = None
    last_name : str

    roll_no : str | None = None

    team_id : str | None = None

    email : EmailStr
    mobile : str | None = None

    is_active : bool    
    is_allowed : bool    
    is_superuser : bool


class UserGroupsUpdate(BaseModel):
    group_ids : list[str]