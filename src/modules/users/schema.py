from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):

    first_name : str
    middle_name : str | None = None
    last_name : str

    roll_no : str | None = None

    email : EmailStr
    mobile : str | None = None

    password : str


class UserResponse(BaseModel):

    id : str

    name : str
    first_name : str
    middle_name : str | None = None
    last_name : str

    roll_no : str | None = None

    email : EmailStr
    mobile : str | None = None

    is_active : bool    
    is_allowed : bool    
    is_superuser : bool


class UserGroupsUpdate(BaseModel):
    group_ids : list[str]