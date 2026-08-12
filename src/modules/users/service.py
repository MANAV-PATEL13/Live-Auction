from src.modules.users.model import User
from src.modules.users.schema import UserCreate
from src.modules.users.repository import UserRepository
from src.core.security import hash_password
from src.common.exceptions import EmailAreadyExistsException

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
            password_hash=hash_password(data.password)
        )

        return await self.repo.create(user)