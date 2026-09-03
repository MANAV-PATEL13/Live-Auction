from beanie import PydanticObjectId

from src.modules.registration.model import Registration


class RegistrationRepository:

    async def create(
            self,
            registration : Registration,
    ) -> Registration:

        await registration.insert()

        return registration



    async def get_by_id(
            self,
            registration_id : PydanticObjectId
    ) -> Registration | None:

        return await Registration.get(
            registration_id
        )


    async def get_by_user_id(
            self,
            user_id : PydanticObjectId
    ) -> Registration | None:

        return await Registration.find_one(
            Registration.user_id == user_id
        )


    async def get_all(
            self,
    ) -> list[Registration]:
        
        return await Registration.find_all().to_list()


    async def update(
            self,
            registration : Registration,
    ) -> Registration:

        await registration.save()

        return registration

    async def delete(
            self,
            registration : Registration,
    ) -> None:

        await registration.delete()