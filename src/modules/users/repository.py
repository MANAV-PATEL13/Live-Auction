from bson import ObjectId
from beanie import PydanticObjectId

from src.modules.users.model import User


class UserRepository:

    async def get_by_email(
            self,
            email : str
    ):

        return await User.find_one(
            User.email == email
        )

    async def get_by_id(
            self,
            user_id : str   
    ):
        if not PydanticObjectId.is_valid(user_id):
            return None

        return await User.get(
            PydanticObjectId(user_id)
        )

    async def get_all(self) -> list[User]:
        return await User.find_all().to_list()

    async def create(
            self,
            user : User
    ):

        await user.insert()

        return user

    async def update(
            self,
            user: User,
            data: dict,
    ) -> User:

        for field, value in data.items():
            setattr(user, field, value)

        await user.save()

        return user

    async def delete(
            self,
            user: User,
    ) -> None:

        await user.delete()