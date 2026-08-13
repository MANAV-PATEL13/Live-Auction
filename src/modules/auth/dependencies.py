from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.common.exceptions import InvalidCredentialsException, InvalidEmailCredentialsException, InactiveUserException
from src.core.jwt import decode_token
from src.modules.users.repository import UserRepository

bearer_scheme = HTTPBearer()

user_repository = UserRepository()

async def get_current_user(
        credentials : HTTPAuthorizationCredentials = Depends(
            bearer_scheme
        )
):

    token = credentials.credentials

    try:
        payload = decode_token(token)

    except Exception:
        raise InvalidCredentialsException()

    if payload.get("type") != "access":
        raise InvalidCredentialsException()

    user_id = payload.get("sub")

    if not user_id:
        raise InvalidEmailCredentialsException()

    user = await user_repository.get_by_id(user_id)

    if not user:
        raise InvalidEmailCredentialsException()

    if not user.is_active:
        raise InactiveUserException()

    return user