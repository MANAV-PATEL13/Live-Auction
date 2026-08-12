from src.core.security import verify_password
from src.modules.users.repository import UserRepository

from src.common.exceptions import (
    InactiveUserException,
    InvalidEmailCredentialsException,
    InvalidPasswordCredentialsException,
    UserNotAllowedException 
)

from fastapi import HTTPException, status

from src.core.jwt import create_access_token, create_refresh_token

class AuthService:

    def __init__(self):

        self.repo = UserRepository()


    async def authenticate(
            self,
            email : str,
            password : str
    ):

        user = await self.repo.get_by_email(email)

        if not user:
            return None

        if not verify_password(password, user.password_hash):
            return None

        return user

    async def login(
            self,
            email : str,
            password : str
    ):

        user = await self.repo.get_by_email(email)

        if not user:
            raise InvalidEmailCredentialsException()

        if not verify_password(password, user.password_hash):
            raise InvalidPasswordCredentialsException()

        if not user.is_active:
            raise InactiveUserException()

        if not user.is_allowed:
            raise UserNotAllowedException()

        access_token = create_access_token(
            str(user.id)
        )

        refresh_token = create_refresh_token(
            str(user.id)
        )

        return access_token, refresh_token