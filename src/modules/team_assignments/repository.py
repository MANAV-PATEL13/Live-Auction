from beanie import PydanticObjectId

from src.modules.team_assignments.model import TeamAssignment


class TeamAssignmentRepository:


    async def create(
            self,
            assignment : TeamAssignment,
    ) -> TeamAssignment:

        await assignment.insert()
        return assignment


    async def get_current_by_user(
            self,
            user_id : PydanticObjectId
    ) -> TeamAssignment | None:

        return await TeamAssignment.find_one(
            TeamAssignment.user_id == user_id,
            TeamAssignment.is_current == True,
        )


    async def get_current_by_team(
            self,
            team_id : PydanticObjectId
    ) -> list[TeamAssignment]:

        return await TeamAssignment.find(
            TeamAssignment.team_id == team_id,
            TeamAssignment.is_current == True
        ).to_list()


    async def get_history_by_user(
            self,
            user_id : PydanticObjectId
    ) -> list[TeamAssignment]:

        return await TeamAssignment.find(
            TeamAssignment.user_id == user_id
        ).sort(
            -TeamAssignment.assigned_at
        ).to_list()


    async def get_by_id(
            self,
            assignment_id : PydanticObjectId
    ) -> TeamAssignment | None:

        return await TeamAssignment.get(assignment_id)


    async def update(
            self,
            assignment : TeamAssignment
    ) -> TeamAssignment:

        await assignment.save()

        return assignment