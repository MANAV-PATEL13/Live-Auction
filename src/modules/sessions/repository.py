from datetime import datetime, timezone
from beanie import PydanticObjectId

from src.modules.sessions.model import Session


class SessionRepository:

    async def create(
            self,
            session : Session
    ) -> Session:

        await session.insert()

        return session

    async def get_active_by_user(
            self,
            user_id : PydanticObjectId
    ) -> Session | None:

        return await Session.find_one(
            Session.user_id == user_id,
            Session.is_active == True,
        )

    async def get_by_id(
            self,
            session_id : PydanticObjectId
    ) -> Session | None:

        return await Session.get(session_id)

    async def invalidate(
            self,
            session : Session,
            reason : str,
    ) -> Session:

        now = datetime.now(timezone.utc)

        session.is_active = False
        session.invalidated_at = now
        session.invalidated_reason = reason

        await session.save()

        return session

    async def logout(
            self,
            session : Session
    ) -> Session:

        now = datetime.now(timezone.utc)

        session.is_active = False
        session.logout_at = now
        session.invalidated_reason = "User Logout Successfully "

        await session.save()

        return session

    async def get_user_history(
            self,
            user_id : PydanticObjectId
    ) -> list[Session]:

        return await Session.find(
            Session.user_id == user_id
        ).sort(
            -Session.login_at
        ).to_list()