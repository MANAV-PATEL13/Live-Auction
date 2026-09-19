from fastapi import APIRouter, Depends, Query, UploadFile, File, Response
from beanie import PydanticObjectId

from src.common.exceptions import AppException, ForbiddenException
from src.common.utils import success_response
from src.modules.auth.dependencies import require_permission, check_user_permission
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


# --- CSV Import & Export ---
@router.post("/import-csv")
async def import_teams_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission("team:create")),
):
    if not file:
        raise AppException(message="CSV file is required", code=400)
    if not file.filename.lower().endswith(".csv"):
        raise AppException(message="Only CSV files are allowed", code=400)

    content = await file.read()
    result = await service.import_csv(content, current_user.id)

    return success_response(
        code=200,
        message="Team CSV import completed",
        data=result.model_dump(),
    )


@router.get("/export-csv")
async def export_teams_csv(
    current_user: User = Depends(require_permission("team:view")),
):
    return await service.export_csv()


@router.get("/import-template")
async def get_import_template(
    current_user: User = Depends(require_permission("team:view")),
):
    csv_content = "name,code,image_url,captain\nRoyal Strikers,RS,https://example.com/logo.png,CS202601\nTitan Warriors,TW,,CS202602\n"
    return Response(
        content=csv_content.encode("utf-8-sig"),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="teams_import_template.csv"',
        },
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
    teams = await service.get_all_with_counts()

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
    team_members = await User.find(User.team_id == team.id).to_list()
    squad_ids = set(str(u.id) for u in team_members)
    if team.captain_id:
        squad_ids.add(str(team.captain_id))
    if team.vice_captain_id:
        squad_ids.add(str(team.vice_captain_id))
    count = len(squad_ids)
    t_dict = team.model_dump()
    t_dict["id"] = str(team.id)
    t_dict["member_count"] = count
    t_dict["members_count"] = count
    t_dict["player_count"] = count
    t_dict["players_count"] = count

    return success_response(
        code=200,
        message="Team fetched successfully",
        data=TeamResponse(**t_dict),
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
        vice_captain_price=data.vice_captain_price or 0,
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
    can_view_all = (
        current_user.is_superuser
        or await check_user_permission(current_user, "team:viewall")
        or await check_user_permission(current_user, "team:update")
    )

    if not can_view_all:
        user_team_id = str(current_user.team_id) if current_user.team_id else None
        user_id_str = str(current_user.id)
        team = await service.get_by_id(PydanticObjectId(team_id))
        is_own_team = (
            (user_team_id and str(team.id) == user_team_id)
            or (team.captain_id and str(team.captain_id) == user_id_str)
            or (team.vice_captain_id and str(team.vice_captain_id) == user_id_str)
        )
        if not is_own_team:
            raise ForbiddenException("You can only view your own team members")

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