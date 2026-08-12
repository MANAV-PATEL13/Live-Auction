from datetime import datetime, timezone, timedelta

import jwt

from src.core.config import settings


def create_token(
        user_id : str,
        token_type : str,
        expires_delta : timedelta,
) -> str:

    now = datetime.now(timezone.utc)

    payload = {
        "sub" : user_id,
        "type" : token_type,
        "iat" : now,
        "exp" : now + expires_delta
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )


def create_access_token(user_id : str) -> str:

    return create_token(
        user_id=user_id,
        token_type="access",
        expires_delta=timedelta(
            days=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )


def create_refresh_token(user_id : str) -> str:

    return create_token(
        user_id=user_id,
        token_type="refresh",
        expires_delta=timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    )