from beanie import PydanticObjectId

from src.modules.users.model import User
from src.modules.users.schema import UserCreate, UserGroupsUpdate
from src.modules.users.repository import UserRepository
from src.core.security import hash_password
from src.common.exceptions import EmailAreadyExistsException, NotFoundException, AppException


class UserService:

    def __init__(self):
        self.repo = UserRepository()


    async def create_user(
            self,
            data : UserCreate,
    ):

        email = str(data.email).lower().strip()

        existing_user = await self.repo.get_by_email(
            email
        )

        if existing_user:
            raise EmailAreadyExistsException()

        name_parts = [
            data.first_name.strip(),
            data.middle_name.strip() if data.middle_name else None,
            data.last_name.strip()
        ]

        name = " ".join(
            part for part in name_parts
            if part
        )

        roll_no=(
            data.roll_no.strip()
            if data.roll_no
            else None
        ),

        mobile=(
            data.mobile.strip()
            if data.mobile
            else None
        ),


        user = User(
            name = name,
            first_name= data.first_name.strip(),
            middle_name=(
                data.middle_name.strip()
                if data.middle_name
                else None
            ),
            last_name=data.last_name.strip(),
            roll_no=roll_no,
            email=email,
            mobile=mobile,
            password_hash=hash_password(data.password),

        )

        return await self.repo.create(user)

    async def get_by_id(
            self,
            user_id: str,
    ) -> User:

        user = await self.repo.get_by_id(user_id)

        if not user:
            raise NotFoundException("User not found")

        return user

    async def get_all(self) -> list[User]:
        return await self.repo.get_all()


    async def assign_team(
        self,
        user_id: str,
        team_id: PydanticObjectId | None,
    ) -> User:

        user = await self.get_by_id(user_id)

        return await self.repo.update(
            user,
            {
                "team_id": team_id,
            },
        )


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