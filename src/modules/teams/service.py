from beanie import PydanticObjectId

from src.modules.teams.model import Team
from src.modules.teams.schema import TeamCreate, TeamUpdate
from src.modules.teams.repository import TeamRepository
from src.modules.users.model import User
from src.common.exceptions import NotFoundException, ConflictException


class TeamService:

    def __init__(
            self,
            repository : TeamRepository
        ):

        self.repository = repository

    async def create(
            self,
            data : TeamCreate,
            current_user : User
    ) -> Team:

        existing = await self.repository.get_by_code(data.code)

        if existing:
            raise ConflictException(
                f"Team with code '{data.code}' already exists"
            )

        team = Team(
            name=data.name,
            code = data.code,
            image_url=data.image_url,
            captain_id=(
                PydanticObjectId(data.captain_id)
                if data.captain_id
                else None
            ),
            vice_captain_id=(
                PydanticObjectId(data.vice_captain_id)
                if data.vice_captain_id
                else None
            ),
            is_active=data.is_active,
            created_by=current_user.id,
            updated_by=current_user.id,
        )

        return await self.repository.create(team)

    async def get_by_id(
            self,
            team_id : PydanticObjectId
    ) -> Team:

        team = await self.repository.get_by_id(team_id)

        if not team:
            raise NotFoundException("Team not found")

        return team

    async def get_all(
            self
    ) -> list[Team]:

        return await self.repository.get_all()


    async def update(
        self,
        team_id: PydanticObjectId,
        data: TeamUpdate,
        current_user: User,
    ) -> Team:

        team = await self.get_by_id(team_id)

        update_data = data.model_dump(
            exclude_unset=True
        )

        # If code is being changed, check duplicate
        if "code" in update_data:

            existing = await self.repository.get_by_code(
                update_data["code"]
            )

            if existing and existing.id != team.id:
                raise ConflictException(
                    f"Team with code '{update_data['code']}' already exists"
                )

        for field, value in update_data.items():

            if field in {
                "captain_id",
                "vice_captain_id",
            }:
                value = (
                    PydanticObjectId(value)
                    if value
                    else None
                )

            setattr(team, field, value)

        team.mark_updated(current_user.id)

        return await self.repository.update(team)

    async def delete(
        self,
        team_id: PydanticObjectId,
    ) -> None:

        team = await self.get_by_id(team_id)

        await self.repository.delete(team)