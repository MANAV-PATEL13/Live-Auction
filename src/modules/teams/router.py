from fastapi import APIRouter, Depends
from beanie import PydanticObjectId

from src.modules.teams.schema import TeamCreate, TeamUpdate 

from src.modules.teams.service import TeamService
from src.modules.teams.repository import TeamRepository
from src.modules.users.model import User

from src.common.utils import success_response
from src.modules.auth.dependencies import require_permission


router = APIRouter(
    prefix="/teams",
    tags=["Teams"],
)

repository = TeamRepository()
service = TeamService(repository)


@router.post("")
async def create_team(
    data: TeamCreate,
    current_user: User = Depends(
        require_permission("team:create")
    ),
):
    team = await service.create(data, current_user)

    return success_response(
        code=201,
        message="Team created successfully",
        data=team,
    )


@router.get("")
async def get_all_teams(
    current_user: User = Depends(
        require_permission("team:view")
    ),
):
    teams = await service.get_all()

    return success_response(
        code=200,
        message="Teams fetched successfully",
        data=teams,
    )


@router.get("/{team_id}")
async def get_team(
    team_id: PydanticObjectId,
    current_user: User = Depends(
        require_permission("team:view")
    ),
):
    team = await service.get_by_id(team_id)

    return success_response(
        code=200,
        message="Team fetched successfully",
        data=team,
    )


@router.put("/{team_id}")
async def update_team(
    team_id: PydanticObjectId,
    data: TeamUpdate,
    current_user: User = Depends(
        require_permission("team:update")
    ),
):
    team = await service.update(
        team_id,
        data,
        current_user,
    )

    return success_response(
        code=200,
        message="Team updated successfully",
        data=team,
    )


@router.delete("/{team_id}")
async def delete_team(
    team_id: PydanticObjectId,
    current_user: User = Depends(
        require_permission("team:delete")
    ),
):
    await service.delete(team_id)

    return success_response(
        code=200,
        message="Team deleted successfully",
        data=None,
    )