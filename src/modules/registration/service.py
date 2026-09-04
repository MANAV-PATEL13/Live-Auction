from beanie import PydanticObjectId

from src.common.exceptions import ConflictException, NotFoundException

from src.modules.registration.model import Registration
from src.modules.registration.repository import RegistrationRepository
from src.modules.registration.schema import RegistrationCreate, RegistrationUpdate

from src.modules.users.model import User

class RegistrationService:

    def __init__(
            self,
            repository : RegistrationRepository
            ):

        self.repository = repository


    async def get_by_user_id(
            self,
            user_id : PydanticObjectId
    ) -> Registration | None:

        return await self.repository.get_by_user_id(
            user_id
        )


    async def get_by_id(
            self,
            registration_id : PydanticObjectId
    ) -> Registration:

        registration = await self.repository.get_by_id(
            registration_id
        )

        if not registration:
            raise NotFoundException(
                "Registration not found"
            )

        return registration

    async def create(
            self,
            data : RegistrationCreate,
            current_user : User,
    ) -> Registration:

        existing = await self.repository.get_by_user_id(
            current_user.id
        )

        if existing:
            raise ConflictException(
                "User has already completed registration"
            )

        registration = Registration(

            user_id = current_user.id,

            tshirt_size=data.tshirt_size,

            cricket=data.cricket,
            volleyball=data.volleyball,
            kabaddi=data.kabaddi,
            kho_kho=data.kho_kho,
            foosball=data.foosball,
            frisbee=data.frisbee,
            dodge_ball=data.dodge_ball,
            chess=data.chess,
            carrom=data.carrom,
            tennis=data.tennis,

            single_talent=(
                data.single_talent.strip()
                if data.single_talent
                else None
            ),

            group_talent_contribution=(
                data.group_talent_contribution
            ),

            qna_contribution=(
                data.qna_contribution
            ),

            created_by=current_user.id,
            updated_by=current_user.id,

        )

        return await self.repository.create(
            registration
        )


    async def update(
            self,
            registration_id : PydanticObjectId,
            data : RegistrationUpdate,
            current_user : User,
    ) -> Registration:


        registration = await self.repository.get_by_id(
            registration_id
        )

        if not registration:
            raise NotFoundException(
                "Registration not found"
            )

        update_data = data.model_dump(
            exclude_unset=True
        )

        if "single_talent" in update_data:

            value = update_data["single_talent"]

            update_data["single_talent"] = (
                value.strip()
                if value
                else None
            )


        for field, value in update_data.items():
            setattr(
                registration,
                field,
                value
            )

        registration.mark_updated(current_user.id)

        return await self.repository.update(
            registration
        )


    async def get_all(
            self,
    ) -> list[Registration]:

        return await self.repository.get_all()