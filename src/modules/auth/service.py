from src.core.security import verify_password
from src.modules.users.repository import UserRepository
from src.modules.sessions.repository import SessionRepository
from src.modules.sessions.service import SessionService
from beanie import PydanticObjectId

from src.common.exceptions import (
    InactiveUserException,
    InvalidCredentialsException,
    UserNotAllowedException,
    InvalidTokenException
)

from fastapi import HTTPException, status

from src.core.jwt import create_access_token, create_refresh_token, decode_token

class AuthService:

    def __init__(self):

        self.repo = UserRepository()
        self.session_repository = SessionRepository()
        self.session_service = SessionService(
            self.session_repository
        )


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
            password : str,
            device_id : str,
            device_name : str | None= None,
            platform : str | None = None
    ):

        user = await self.repo.get_by_email(email)

        if not user:
            raise InvalidCredentialsException()

        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsException()

        if not user.is_active:
            raise InactiveUserException()

        if not user.is_allowed:
            raise UserNotAllowedException()


        session = await self.session_service.create_login_session(
            user=user,
            device_id=device_id,
            device_name=device_name,
            platform=platform
        )


        # create access token
        access_token = create_access_token(
            str(user.id),
            str(session.id)
        )

        refresh_token = create_refresh_token(
            str(user.id),
            str(session.id),
        )

        return access_token, refresh_token

    async def refresh_access_token(
        self,
        refresh_token: str,
    ):

        try:
            payload = decode_token(refresh_token)

        except Exception:
            raise InvalidTokenException()

        if payload.get("type") != "refresh":
            raise InvalidCredentialsException()

        user_id = payload.get("sub")

        if not user_id:
            raise InvalidCredentialsException()

       

        session_id = payload.get("session_id")

        if not session_id:
            raise InvalidTokenException()

        session = await self.session_repository.get_by_id(
            PydanticObjectId(session_id)
        )

        if not session:
            raise InvalidTokenException()

        if not session.is_active:
            raise InvalidTokenException()

        if session.user_id != PydanticObjectId(user_id):
            raise InvalidTokenException()
        
        # Validate user
        user = await self.repo.get_by_id(user_id)

        if not user:
            raise InvalidCredentialsException()

        if not user.is_active:
            raise InactiveUserException()

        if not user.is_allowed:
            raise UserNotAllowedException()

        access_token = create_access_token(
            str(user.id),
            str(session.id),
        )

        return access_token