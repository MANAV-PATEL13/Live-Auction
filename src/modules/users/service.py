from src.modules.users.model import User
from src.modules.users.schema import UserCreate, UserGroupsUpdate
from src.modules.users.repository import UserRepository
from src.core.security import hash_password
from src.common.exceptions import EmailAreadyExistsException, AppException


class UserService:

    def __init__(self):

        self.repo = UserRepository()


    async def create_user(
            self,
            data : UserCreate,
    ):

        existing_user = await self.repo.get_by_email(
            data.email
        )

        if existing_user:
            raise EmailAreadyExistsException()

        name_parts = [
            data.first_name,
            data.middle_name,
            data.last_name
        ]

        name = " ".join(
            part for part in name_parts
            if part
        )


        user = User(
            name = name,
            first_name= data.first_name,
            middle_name=data.middle_name,
            last_name=data.last_name,
            roll_no=data.roll_no,
            email=data.email,
            mobile=data.mobile,
            password_hash=hash_password(data.password),

        )

        return await self.repo.create(user)

    async def get_by_id(
            self,
            user_id: str,
    ) -> User:

        user = await self.repo.get_by_id(user_id)

        if not user:
            raise AppException(
                message="User not found",
                code=404,
            )

        return user

    async def get_all(self) -> list[User]:
        return await self.repo.get_all()

    async def update_groups(
            self,
            user_id: str,
            data: UserGroupsUpdate,
    ) -> User:

        user = await self.get_by_id(user_id)

        return await self.repo.update(
            user,
            {"group_ids": data.group_ids},
        )

    async def reactivate(
            self,
            user_id: str,
    ) -> User:

        user = await self.get_by_id(user_id)

        return await self.repo.update(
            user,
            {"is_allowed": True},
        )
    
    async def deactivate(
            self,
            user_id: str,
    ) -> User:

        user = await self.get_by_id(user_id)

        return await self.repo.update(
            user,
            {"is_allowed": False},
        )

    async def delete(
            self,
            user_id: str,
    ) -> None:

        user = await self.get_by_id(user_id)

        await self.repo.update(
            user,
            {"is_active": False},
        )