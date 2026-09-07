from beanie import PydanticObjectId

from src.common.exceptions import ConflictException, NotFoundException
from src.modules.team_assignments.repository import TeamAssignmentRepository
from src.modules.teams.model import Team
from src.modules.teams.repository import TeamRepository
from src.modules.teams.schema import TeamCreate, TeamUpdate
from src.modules.teams.wallet_model import TeamWalletTransaction, TransactionType
from src.modules.teams.wallet_repository import TeamWalletRepository
from src.modules.users.model import User
from src.modules.users.repository import UserRepository


class TeamService:

    def __init__(
        self,
        repository: TeamRepository,
        user_repository: UserRepository,
    ):
        self.repository = repository
        self.user_repository = user_repository
        self.wallet_repository = TeamWalletRepository()
        self.assignment_repository = TeamAssignmentRepository()

    # Helpers
    @staticmethod
    def _normalize_name(value: str) -> str:
        return value.strip()

    @staticmethod
    def _normalize_code(value: str) -> str:
        return value.strip().upper()

    async def _validate_user_exists(
        self,
        user_id: str | None,
    ) -> PydanticObjectId | None:
        if not user_id:
            return None

        if not PydanticObjectId.is_valid(user_id):
            raise NotFoundException("User not found")

        object_id = PydanticObjectId(user_id)
        user = await self.user_repository.get_by_id(object_id)

        if not user:
            raise NotFoundException("User not found")

        if not user.is_active:
            raise ConflictException("User is inactive")

        if not user.is_allowed:
            raise ConflictException("User is not allowed")

        return object_id

    async def _validate_team_member(
        self,
        team_id: PydanticObjectId,
        user_id: str | None,
        role_name: str = "Captain",
    ) -> PydanticObjectId | None:
        if not user_id:
            return None

        object_id = await self._validate_user_exists(user_id)
        user = await self.user_repository.get_by_id(object_id)

        # Enforce rule: Captain / Vice-Captain must be a current member of that team
        if user.team_id != team_id:
            raise ConflictException(
                f"{role_name} must be a current member of this team"
            )

        if role_name == "Captain":
            existing = await self.repository.get_by_caption_id(object_id)
            if existing and existing.id != team_id:
                raise ConflictException(
                    f"User is already captain of team '{existing.name}'"
                )
        elif role_name == "Vice-Captain":
            existing = await self.repository.get_by_vice_caption_id(object_id)
            if existing and existing.id != team_id:
                raise ConflictException(
                    f"User is already vice-captain of team '{existing.name}'"
                )

        return object_id

    async def create(
        self,
        data: TeamCreate,
        current_user: User,
    ) -> Team:
        name = self._normalize_name(data.name)
        code = self._normalize_code(data.code)

        existing = await self.repository.get_by_code(code)
        if existing:
            raise ConflictException(f"Team with code '{code}' already exists")

        # If captain or vice-captain passed during creation, ensure they are not identical
        if data.captain_id and data.vice_captain_id and data.captain_id == data.vice_captain_id:
            raise ConflictException(
                "Captain and vice-captain cannot be the same user"
            )

        # Note: Members must be assigned to team before becoming captain/vice-captain
        if data.captain_id or data.vice_captain_id:
            raise ConflictException(
                "Players must first be assigned to the team before appointing Captain or Vice-Captain"
            )

        team = Team(
            name=name,
            code=code,
            image_url=data.image_url,
            captain_id=None,
            vice_captain_id=None,
            initial_balance=data.initial_balance,
            balance=data.initial_balance,
            is_active=data.is_active,
            created_by=current_user.id,
            updated_by=current_user.id,
        )

        return await self.repository.create(team)

    async def get_by_id(
        self,
        team_id: PydanticObjectId,
    ) -> Team:
        team = await self.repository.get_by_id(team_id)
        if not team:
            raise NotFoundException("Team not found")
        return team

    async def get_all(
        self,
        active_only: bool = False,
    ) -> list[Team]:
        return await self.repository.get_all(active_only=active_only)

    async def update(
        self,
        team_id: PydanticObjectId,
        data: TeamUpdate,
        current_user: User,
    ) -> Team:
        team = await self.get_by_id(team_id)

        update_data = data.model_dump(exclude_unset=True)

        if "name" in update_data:
            update_data["name"] = self._normalize_name(update_data["name"])

        # If code is being changed, check duplicate
        if "code" in update_data:
            update_data["code"] = self._normalize_code(update_data["code"])
            existing = await self.repository.get_by_code(update_data["code"])
            if existing and existing.id != team.id:
                raise ConflictException(
                    f"Team with code '{update_data['code']}' already exists"
                )

        # Validate captain if provided
        if "captain_id" in update_data:
            update_data["captain_id"] = await self._validate_team_member(
                team.id, update_data["captain_id"], "Captain"
            )

        # Validate vice_captain if provided
        if "vice_captain_id" in update_data:
            update_data["vice_captain_id"] = await self._validate_team_member(
                team.id, update_data["vice_captain_id"], "Vice-Captain"
            )

        captain_id = update_data.get("captain_id", team.captain_id)
        vice_captain_id = update_data.get("vice_captain_id", team.vice_captain_id)

        if captain_id and vice_captain_id and captain_id == vice_captain_id:
            raise ConflictException(
                "Captain and vice-captain cannot be the same user"
            )

        for field, value in update_data.items():
            setattr(team, field, value)

        team.mark_updated(current_user.id)
        return await self.repository.update(team)

    async def set_captain(
        self,
        team_id: PydanticObjectId,
        captain_id: str,
        current_user: User,
    ) -> Team:
        team = await self.get_by_id(team_id)
        cid = await self._validate_team_member(team.id, captain_id, "Captain")

        if cid and team.vice_captain_id and cid == team.vice_captain_id:
            raise ConflictException(
                "Captain and Vice-Captain cannot be the same user"
            )

        team.captain_id = cid
        team.mark_updated(current_user.id)
        return await self.repository.update(team)

    async def remove_captain(
        self,
        team_id: PydanticObjectId,
        current_user: User,
    ) -> Team:
        team = await self.get_by_id(team_id)
        team.captain_id = None
        team.mark_updated(current_user.id)
        return await self.repository.update(team)

    async def set_vice_captain(
        self,
        team_id: PydanticObjectId,
        vice_captain_id: str,
        current_user: User,
    ) -> Team:
        team = await self.get_by_id(team_id)
        vcid = await self._validate_team_member(
            team.id, vice_captain_id, "Vice-Captain"
        )

        if vcid and team.captain_id and vcid == team.captain_id:
            raise ConflictException(
                "Captain and Vice-Captain cannot be the same user"
            )

        team.vice_captain_id = vcid
        team.mark_updated(current_user.id)
        return await self.repository.update(team)

    async def remove_vice_captain(
        self,
        team_id: PydanticObjectId,
        current_user: User,
    ) -> Team:
        team = await self.get_by_id(team_id)
        team.vice_captain_id = None
        team.mark_updated(current_user.id)
        return await self.repository.update(team)

    async def deactivate(
        self,
        team_id: PydanticObjectId,
        current_user: User,
    ) -> Team:
        team = await self.get_by_id(team_id)
        if not team.is_active:
            return team

        team.is_active = False
        team.mark_updated(current_user.id)
        return await self.repository.update(team)

    # --- Wallet & Ledger ---
    async def get_wallet_summary(
        self,
        team_id: PydanticObjectId,
    ) -> dict:
        team = await self.get_by_id(team_id)
        transactions = await self.wallet_repository.get_by_team(
            team_id, skip=0, limit=1000
        )
        total_tx = await self.wallet_repository.count_by_team(team_id)
        active_members = await self.assignment_repository.get_current_by_team(
            team_id
        )

        total_spent = sum(-t.amount for t in transactions if t.amount < 0)
        total_refunded = sum(t.amount for t in transactions if t.amount > 0)

        return {
            "team_id": str(team.id),
            "team_name": team.name,
            "initial_balance": team.initial_balance,
            "balance": team.balance,
            "total_spent": total_spent,
            "total_refunded": total_refunded,
            "active_players_count": len(active_members),
            "total_transactions": total_tx,
        }

    async def get_transactions(
        self,
        team_id: PydanticObjectId,
        skip: int = 0,
        limit: int = 50,
    ) -> list[TeamWalletTransaction]:
        await self.get_by_id(team_id)
        return await self.wallet_repository.get_by_team(team_id, skip=skip, limit=limit)

    async def manual_adjust_balance(
        self,
        team_id: PydanticObjectId,
        amount: int,
        description: str,
        current_user: User,
    ) -> TeamWalletTransaction:
        if amount == 0:
            raise ConflictException("Adjustment amount cannot be zero")

        team = await self.get_by_id(team_id)

        if team.balance + amount < 0:
            raise ConflictException(
                f"Adjustment would result in negative balance. Current: {team.balance}, Adjustment: {amount}"
            )

        balance_before = team.balance
        balance_after = team.balance + amount
        team.balance = balance_after
        team.mark_updated(current_user.id)
        await self.repository.update(team)

        tx = TeamWalletTransaction(
            team_id=team.id,
            transaction_type=TransactionType.MANUAL_ADJUSTMENT,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description,
            created_by=current_user.id,
        )
        return await self.wallet_repository.create(tx)