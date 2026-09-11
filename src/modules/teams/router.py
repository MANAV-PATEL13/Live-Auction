from fastapi import APIRouter, Depends, Query
from beanie import PydanticObjectId

from src.common.utils import success_response
from src.modules.auth.dependencies import require_permission
from src.modules.teams.schema import (
    TeamCreate,
    TeamUpdate,
    TeamResponse,
    WalletAdjustmentRequest,
    TeamMemberAssignmentRequest,
    TeamMemberTransferRequest,
    TeamLeadershipUpdate,
)
from src.modules.teams.service import TeamService
from src.modules.users.model import User


router = APIRouter(
    prefix="/teams",
    tags=["Teams"],
)

service = TeamService()


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


# --- Team Members Management ---
@router.get("/{team_id}/members")
async def get_team_members(
    team_id: str,
    current_user: User = Depends(
        require_permission("team:view")
    ),
):
    users = await service.get_members(team_id)

    return success_response(
        code=200,
        message="Team members fetched successfully",
        data=users,
    )


@router.post("/{team_id}/members/{user_id}")
async def assign_member(
    team_id: str,
    user_id: str,
    data: TeamMemberAssignmentRequest,
    current_user: User = Depends(
        require_permission("team:update")
    ),
):
    user = await service.assign_member(
        team_id=team_id,
        user_id=user_id,
        price=data.price,
        current_user=current_user,
    )

    return success_response(
        code=200,
        message="User assigned to team successfully",
        data={
            "user_id": str(user.id),
            "team_id": str(user.team_id),
            "team_price": user.team_price,
        },
    )


@router.delete("/{team_id}/members/{user_id}")
async def remove_member(
    team_id: str,
    user_id: str,
    current_user: User = Depends(
        require_permission("team:update")
    ),
):
    user = await service.remove_member(
        team_id=team_id,
        user_id=user_id,
        current_user=current_user,
    )

    return success_response(
        code=200,
        message="User removed from team successfully",
        data={
            "user_id": str(user.id),
            "team_id": None,
            "team_price": user.team_price,
        },
    )


@router.post("/{destination_team_id}/members/{user_id}/transfer")
async def transfer_member(
    destination_team_id: str,
    user_id: str,
    data: TeamMemberTransferRequest,
    current_user: User = Depends(
        require_permission("team:update")
    ),
):
    user = await service.transfer_member(
        destination_team_id=destination_team_id,
        user_id=user_id,
        source_team_id=data.source_team_id,
        price=data.price,
        current_user=current_user,
    )

    return success_response(
        code=200,
        message="User transferred successfully",
        data={
            "user_id": str(user.id),
            "team_id": str(user.team_id),
            "team_price": user.team_price,
        },
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
            "reference_id": tx.reference_id,
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