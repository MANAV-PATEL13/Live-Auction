from datetime import datetime, timezone

from beanie import PydanticObjectId

from src.modules.users.model import User


class UserRepository:

    async def get_by_email(
            self,
            email : str
    ) -> User | None:
        
        return await User.find_one(
            User.email == email.lower().strip()
        )

    async def get_by_id(
            self,
            user_id : str | PydanticObjectId
    )-> User | None:
               
        if not PydanticObjectId.is_valid(user_id):
            return None

        return await User.get(
            PydanticObjectId(user_id)
        )

    async def get_all(
            self,
        ) -> list[User]:
        
        return await User.find_all().to_list()

    async def create(
            self,
            user : User
    ) -> User:

        await user.insert()

        return user

    async def update(
            self,
            user: User,
            data: dict,
    ) -> User:

        for field, value in data.items():
            setattr(user, field, value)

        user.updated_at = datetime.now(timezone.utc)

        await user.save()

        return user

       
    async def delete(
            self,
            user: User,
    ) -> None:

        await user.delete()

    async def get_by_team_id(
        self,
        team_id: PydanticObjectId,
    ) -> list[User]:
        return await User.find(
            User.team_id == team_id
        ).to_list()