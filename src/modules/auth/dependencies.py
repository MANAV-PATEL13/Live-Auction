from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from beanie import PydanticObjectId
from beanie.operators import In

from src.common.exceptions import (
    InvalidCredentialsException,
    InactiveUserException,
    InvalidTokenException,
    InvalidSessionException,
    UserNotAllowedException,
    ForbiddenException,
)
from src.core.jwt import decode_token
from src.modules.users.model import User
from src.modules.users.repository import UserRepository
from src.modules.permission_groups.model import PermissionGroup
from src.modules.permissions.model import Permission
from src.modules.permissions.repository import PermissionRepository

from src.modules.sessions.repository import SessionRepository
from src.modules.sessions.service import SessionService

bearer_scheme = HTTPBearer()

user_repository = UserRepository()

permissions = PermissionRepository()

session_repository = SessionRepository()

session_service = SessionService(session_repository)


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> User:

    token = credentials.credentials

    try:
        payload = decode_token(token)

    except Exception:
        raise InvalidTokenException()

    if payload.get("type") != "access":
        raise InvalidTokenException()

    user_id = payload.get("sub")

    if not user_id:
        raise InvalidCredentialsException()

    session_id = payload.get("session_id")

    if not session_id:
        raise InvalidTokenException()

    await session_service.validate_session(
        session_id=PydanticObjectId(session_id),
        user_id=PydanticObjectId(user_id)
    )
    
    user = await user_repository.get_by_id(user_id)

    if not user:
        raise InvalidCredentialsException()

    if not user.is_allowed:
        raise UserNotAllowedException()

    if not user.is_active:
        raise InactiveUserException()

    return user


async def check_user_permission(current_user: User, permission_code: str) -> bool:
    # Superusers always pass
    if current_user.is_superuser:
        return True

    if not current_user.group_ids:
        return False

    # Resolve group ObjectIds
    valid_group_ids = [
        PydanticObjectId(gid)
        for gid in current_user.group_ids
        if PydanticObjectId.is_valid(gid)
    ]

    if not valid_group_ids:
        return False

    # Load all active groups the user belongs to
    groups = await PermissionGroup.find(
        In(PermissionGroup.id, valid_group_ids),
        PermissionGroup.is_active == True,
    ).to_list()

    # Aggregate all permission_ids across groups
    all_permission_ids: list[str] = []
    for group in groups:
        all_permission_ids.extend(group.permission_ids)

    if not all_permission_ids:
        return False

    # Resolve permission ObjectIds
    valid_permission_ids = [
        PydanticObjectId(pid)
        for pid in all_permission_ids
        if PydanticObjectId.is_valid(pid)
    ]

    if not valid_permission_ids:
        return False

    # Check if the required permission exists and is active
    permission = await Permission.find_one(
        In(Permission.id, valid_permission_ids),
        Permission.code == permission_code,
        Permission.is_active == True,
    )

    return permission is not None


def require_permission(permission_code: str):
 

    async def check_permission(
            current_user: User = Depends(get_current_user),
    ) -> User:

        # Superusers always pass
        if current_user.is_superuser:
            return current_user

        permission_name = await permissions.get_by_code(permission_code)

        if not permission_name:
            raise ForbiddenException(
                "Permission not exist"
            )

        has_perm = await check_user_permission(current_user, permission_code)
        if not has_perm:
            raise ForbiddenException(
                f"Permission '{permission_name.name}' is required"
            )

        return current_user

    return check_permission