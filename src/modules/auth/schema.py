from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):

    email : EmailStr
    password : str

    device_id : str
    device_name : str | None = None
    platform : str | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):

    access_token : str
    refresh_token : str
    token_type : str = "bearer"