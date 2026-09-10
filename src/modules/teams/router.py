from fastapi import APIRouter, Depends, Query
from beanie import PydanticObjectId

from src.common.utils import success_response
from src.modules.auth.dependencies import get_current_user, require_permission
from src.modules.teams.repository import TeamRepository
from src.modules.teams.schema import (
    TeamCreate,
    TeamUpdate,
    WalletAdjustmentRequest,
    TeamMemberAssign,
    TeamMemberTransferRequest,
    TeamLeadershipUpdate,
    TeamMembersResponse,
)
from src.modules.teams.service import TeamService
from src.modules.users.schema import UserResponse
from src.modules.users.model import User
from src.modules.users.repository import UserRepository


router = APIRouter(
    prefix="/teams",
    tags=["Teams"],
)

repository = TeamRepository()
user_repository = UserRepository()

service = TeamService(
    repository,
    user_repository,
)


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


@router.get(
    "/users/{user_id}/team",
)
async def get_user_team(
    user_id: PydanticObjectId,
    current_user: User = Depends(require_permission("team:view")),
):
    team = await service.get_user_team(user_id)

    return success_response(
        data=(
            TeamResponse.model_validate(team, from_attributes=True)
            if team
            else None
        ),
        message="user team fetched successfully",
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
    team = await service.deactivate(team_id, current_user)

    return success_response(
        code=200,
        message="Team deactivated successfully",
        data=None,
    )


# --- Leadership Management ---
@router.put(
    "/{team_id}/leadership",
)
async def update_leadership(
    team_id: PydanticObjectId,
    data: TeamLeadershipUpdate,
    current_user: User = Depends(require_permission("team:update")),
):
    team = await service.update_leadership(
        team_id=team_id,
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
        current_user_id=current_user.id,
    )

    return success_response(
        data=TeamResponse.model_validate(team, from_attributes=True),
        message="team leadership updated successfully",
    )


@router.get(
    "/{team_id}/members",
)
async def get_team_members(
    team_id: PydanticObjectId,
    current_user: User = Depends(require_permission("team:view")),
):
    team = await service.repository.get_by_id(team_id)

    if not team:
        from src.common.exceptions import NotFoundException
        raise NotFoundException("team not found")

    members = await service.get_team_members(team_id)

    return success_response(
        data=TeamMembersResponse(
            team_id=str(team.id),
            team_name=team.name,
            members=[
                UserResponse.model_validate(member, from_attributes=True)
                for member in members
            ],
        ),
        message="team members fetched successfully",
    )


# --- Wallet & Ledger ---
@router.get("/{team_id}/wallet")
async def get_team_wallet(
    team_id: PydanticObjectId,
    current_user: User = Depends(
        require_permission("team:view")
    ),
):
    wallet = await service.get_wallet_summary(team_id)
    return success_response(
        code=200,
        message="Team wallet summary fetched successfully",
        data=wallet,
    )


@router.get("/{team_id}/transactions")
async def get_team_transactions(
    team_id: PydanticObjectId,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(
        require_permission("team:view")
    ),
):
    transactions = await service.get_transactions(
        team_id=team_id,
        skip=skip,
        limit=limit,
    )
    data = [
        {
            "id": str(tx.id),
            "team_id": str(tx.team_id),
            "transaction_type": tx.transaction_type.value,
            "amount": tx.amount,
            "balance_before": tx.balance_before,
            "balance_after": tx.balance_after,
            "user_id": str(tx.user_id) if tx.user_id else None,
            "description": tx.description,
            "created_by": str(tx.created_by) if tx.created_by else None,
            "created_at": tx.created_at,
        }
        for tx in transactions
    ]
    return success_response(
        code=200,
        message="Team transactions fetched successfully",
        data=data,
    )


@router.post("/{team_id}/wallet/adjust")
async def adjust_team_wallet(
    team_id: PydanticObjectId,
    data: WalletAdjustmentRequest,
    current_user: User = Depends(
        require_permission("team:update")
    ),
):
    tx = await service.manual_adjust_balance(
        team_id=team_id,
        amount=data.amount,
        description=data.description,
        current_user=current_user,
    )
    return success_response(
        code=200,
        message="Team wallet adjusted successfully",
        data={
            "id": str(tx.id),
            "team_id": str(tx.team_id),
            "transaction_type": tx.transaction_type.value,
            "amount": tx.amount,
            "balance_before": tx.balance_before,
            "balance_after": tx.balance_after,
            "description": tx.description,
            "created_at": tx.created_at,
        },
    )


@router.post(
    "/{team_id}/members/{user_id}",
)
async def assign_player(
    team_id: PydanticObjectId,
    user_id: PydanticObjectId,
    data: TeamMemberAssign,
    current_user: User = Depends(require_permission("team:update")),
):
    user = await service.assign_player(
        team_id=team_id,
        user_id=user_id,
        price=data.price,
        current_user_id=current_user.id,
    )

    return success_response(
        data=UserResponse.model_validate(user, from_attributes=True),
        message="player assigned successfully",
    )


@router.delete(
    "/{team_id}/members/{user_id}",
)
async def remove_player(
    team_id: PydanticObjectId,
    user_id: PydanticObjectId,
    current_user: User = Depends(require_permission("team:update")),
):
    user = await service.remove_player(
        team_id=team_id,
        user_id=user_id,
        current_user_id=current_user.id,
    )

    return success_response(
        data=UserResponse.model_validate(user, from_attributes=True),
        message="player removed successfully",
    )


@router.post(
    "/{destination_team_id}/members/{user_id}/transfer",
)
async def transfer_player(
    destination_team_id: PydanticObjectId,
    user_id: PydanticObjectId,
    data: TeamMemberTransferRequest,
    current_user: User = Depends(require_permission("team:update")),
):
    if not PydanticObjectId.is_valid(data.source_team_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid source team ID")

    user = await service.transfer_player(
        source_team_id=PydanticObjectId(data.source_team_id),
        user_id=user_id,
        destination_team_id=destination_team_id,
        current_user_id=current_user.id,
        new_price=data.price,
    )

    return success_response(
        data=UserResponse.model_validate(user, from_attributes=True),
        message="player transferred successfully",
    )