from beanie import PydanticObjectId

from src.modules.teams.model import Team
from src.modules.users.model import User


class TeamRepository:

    async def create(self, team: Team) -> Team:
        await team.insert()
        return team

    async def get_by_id(
        self,
        team_id: PydanticObjectId,
    ) -> Team | None:
        return await Team.get(team_id)

    async def get_by_code(
        self,
        team_code: str,
    ) -> Team | None:
        return await Team.find_one(
            Team.code == team_code
        )

    async def get_by_caption_id(
        self,
        user_id: PydanticObjectId,
    ) -> Team | None:
        return await Team.find_one(
            Team.captain_id == user_id,
            Team.is_active == True,
        )

    async def get_by_vice_caption_id(
        self,
        user_id: PydanticObjectId,
    ) -> Team | None:
        return await Team.find_one(
            Team.vice_captain_id == user_id,
            Team.is_active == True,
        )

    async def get_all(
        self,
        active_only: bool = False,
    ) -> list[Team]:

        if active_only:
            return await Team.find(
                Team.is_active == True
            ).sort("+code", "+name").to_list()

        return await Team.find_all().sort("+code", "+name").to_list()

    async def update(self, team: Team) -> Team:
        await team.save()
        return team

    async def get_members(
        self,
        team_id: PydanticObjectId,
    ) -> list[User]:

        return await User.find(
            User.team_id == team_id
        ).to_list()

    async def get_user_team(
        self,
        user_id: PydanticObjectId,
    ) -> Team | None:

        user = await User.get(user_id)

        if not user or not user.team_id:
            return None

        return await Team.get(user.team_id)
