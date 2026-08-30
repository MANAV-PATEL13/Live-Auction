from beanie import PydanticObjectId

from src.modules.teams.model import Team


class TeamRepository:

    async def create(
            self,
            team : Team
    )->Team :
        
        await team.insert()

        return team


    async def get_by_id(
            self,
            team_id : str,
    ) -> Team | None:

        return await Team.get(team_id)


    async def get_all(
            self,
    ) -> list[Team]:

        return await Team.find_all().to_list()


    async def get_by_code(
            self,
            team_code : str
    ) -> Team | None:

        return await Team.find_one(
            Team.code == team_code
        )


    async def update(
            self,
            team : Team,
    ) -> Team:

        await team.save()

        return team


    async def delete(
            self,
            team : Team
    ) -> None:

        await team.delete()
        