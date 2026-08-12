from src.modules.users.model import User

class UserRepository:

    async def get_by_email(
            self,
            email : str
    ):

        return await User.find_one(
            User.email == email
        )


    async def create(
            self,
            user : User
    ):

        await user.insert()

        return user