from beanie import PydanticObjectId

from src.modules.sessions.model import Session
from src.modules.sessions.repository import SessionRepository
from src.modules.users.model import User


class SessionService:

    def __init__(
            self,
            repository : SessionRepository,
        ):

        self.repository = repository

    async def create_login_session(
            self,
            user : User,
            device_id : str,
            device_name : str | None = None,
            platform : str | None = None,
    ) -> Session:

        active_session = await self.repository.get_active_by_user(
            user.id
        )

        if active_session:

            await self.repository.invalidate(
                active_session,
                reason="New Device Login"
            )

        session = Session(
            user_id=user.id,
            device_id=device_id,
            device_name=device_name,
            platform = platform,
            is_active=True
        )

        return await self.repository.create(session)


    async def validate_session(
        self,
        session_id: PydanticObjectId,
    ) -> Session | None:

        session = await self.repository.get_by_id(
            session_id
        )

        if not session:
            return None

        if not session.is_active:
            return None

        return session

    async def logout(
        self,
        session_id: PydanticObjectId,
    ) -> Session | None:

        session = await self.repository.get_by_id(
            session_id
        )

        if not session:
            return None

        if session.is_active:
            await self.repository.logout(session)

        return session

    async def get_login_history(
        self,
        user_id: PydanticObjectId,
    ) -> list[Session]:

        return await self.repository.get_user_history(
            user_id
        )