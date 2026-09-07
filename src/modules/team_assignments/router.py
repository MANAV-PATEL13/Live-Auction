from fastapi import APIRouter, Depends

from src.common.utils import success_response
from src.modules.auth.dependencies import get_current_user, require_permission
from src.modules.team_assignments.schema import TeamAssignmentCreate, TeamTransferRequest
from src.modules.team_assignments.service import TeamAssignmentService


router = APIRouter(
    prefix="/team-assignments",
    tags=["Team Assignments"],
)


service = TeamAssignmentService()


@router.post(
    "",
    dependencies=[
        Depends(require_permission("team:assign"))
    ],
)
async def assign_user(
    data: TeamAssignmentCreate,
    current_user=Depends(get_current_user),
):

    assignment = await service.assign_user(
        user_id=data.user_id,
        team_id=data.team_id,
        price=data.price,
        assigned_by=current_user.id,
    )

    return success_response(
        data={
            "id": str(assignment.id),
            "user_id": str(assignment.user_id),
            "team_id": str(assignment.team_id),
            "price": assignment.price,
            "is_current": assignment.is_current,
        },
        message="User assigned to team successfully",
    )


@router.post(
    "/{user_id}/transfer",
    dependencies=[
        Depends(require_permission("team:assign"))
    ],
)
async def transfer_user(
    user_id: str,
    data: TeamTransferRequest,
    current_user=Depends(get_current_user),
):

    assignment = await service.transfer_user(
        user_id=user_id,
        new_team_id=data.new_team_id,
        price=data.price,
        transferred_by=current_user.id,
    )

    return success_response(
        data={
            "id": str(assignment.id),
            "user_id": str(assignment.user_id),
            "team_id": str(assignment.team_id),
            "price": assignment.price,
            "is_current": assignment.is_current,
        },
        message="User transferred successfully",
    )


@router.delete(
    "/{user_id}",
    dependencies=[
        Depends(require_permission("team:assign"))
    ],
)
async def remove_user(
    user_id: str,
    current_user=Depends(get_current_user),
):

    await service.remove_user(
        user_id=user_id,
        removed_by=current_user.id,
    )

    return success_response(
        data=None,
        message="User removed from team successfully",
    )


@router.get(
    "/user/{user_id}",
    dependencies=[
        Depends(require_permission("team:view"))
    ],
)
async def get_user_team(
    user_id: str,
):

    assignment = await service.get_user_team(user_id)

    return success_response(
        data={
            "id": str(assignment.id),
            "user_id": str(assignment.user_id),
            "team_id": str(assignment.team_id),
            "price": assignment.price,
            "assigned_at": assignment.assigned_at,
        },
        message="User team fetched successfully",
    )


@router.get(
    "/team/{team_id}",
    dependencies=[
        Depends(require_permission("team:view"))
    ],
)
async def get_team_members(
    team_id: str,
):

    assignments = await service.get_team_members(team_id)

    data = [
        {
            "id": str(item.id),
            "user_id": str(item.user_id),
            "team_id": str(item.team_id),
            "price": item.price,
            "assigned_at": item.assigned_at,
        }
        for item in assignments
    ]

    return success_response(
        data=data,
        message="Team members fetched successfully",
    )


@router.get(
    "/user/{user_id}/history",
    dependencies=[
        Depends(require_permission("team:view"))
    ],
)
async def get_user_history(
    user_id: str,
):

    assignments = await service.get_user_history(user_id)

    data = [
        {
            "id": str(item.id),
            "user_id": str(item.user_id),
            "team_id": str(item.team_id),
            "price": item.price,
            "assigned_at": item.assigned_at,
            "assigned_by": str(item.assigned_by),
            "removed_at": item.removed_at,
            "removed_by": (
                str(item.removed_by)
                if item.removed_by
                else None
            ),
            "is_current": item.is_current,
        }
        for item in assignments
    ]

    return success_response(
        data=data,
        message="User team history fetched successfully",
    )