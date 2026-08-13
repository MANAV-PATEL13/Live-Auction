from src.modules.users.model import User
from bson import ObjectId

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

        return await User.get(
            ObjectId(user_id)
        )


    async def create(
            self,
            user : User
    ):

        await user.insert()

        return user