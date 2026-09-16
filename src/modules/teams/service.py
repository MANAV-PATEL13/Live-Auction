from datetime import datetime, timezone
from beanie import PydanticObjectId

from src.common.exceptions import AppException, ConflictException, NotFoundException
from src.modules.teams.model import Team
from src.modules.teams.repository import TeamRepository
from src.modules.teams.schema import TeamCreate, TeamUpdate
from src.modules.teams.wallet_constants import WalletTransactionType
from src.modules.teams.wallet_model import TeamWalletTransaction
from src.modules.teams.wallet_repository import TeamWalletRepository
from src.modules.users.model import User
from src.modules.users.repository import UserRepository


class TeamService:

    def __init__(
        self,
        repository: TeamRepository | None = None,
        user_repository: UserRepository | None = None,
    ):
        self.team_repo = repository or TeamRepository()
        self.user_repo = user_repository or UserRepository()
        self.repository = self.team_repo
        self.user_repository = self.user_repo
        self.wallet_repository = TeamWalletRepository()

    # ---------------------------------------------------------
    # HELPERS
    # ---------------------------------------------------------

    @staticmethod
    def _normalize_name(value: str) -> str:
        return value.strip()

    @staticmethod
    def _normalize_code(value: str) -> str:
        return value.strip().upper()

    @staticmethod
    def _object_id(value: str | PydanticObjectId) -> PydanticObjectId:
        if isinstance(value, PydanticObjectId):
            return value

        if not PydanticObjectId.is_valid(value):
            raise AppException(
                message="Invalid ID",
                code=400,
            )

        return PydanticObjectId(value)

    async def _get_active_team(
        self,
        team_id: str | PydanticObjectId,
    ) -> Team:
        object_id = self._object_id(team_id)

        team = await self.team_repo.get_by_id(object_id)

        if not team:
            raise AppException(
                message="Team not found",
                code=404,
            )

        if not team.is_active:
            raise AppException(
                message="Team is inactive",
                code=400,
            )

        return team

    async def _get_active_user(
        self,
        user_id: str | PydanticObjectId,
    ) -> User:
        object_id = self._object_id(user_id)

        user = await self.user_repo.get_by_id(object_id)

        if not user:
            raise AppException(
                message="User not found",
                code=404,
            )

        if not user.is_active:
            raise AppException(
                message="User is inactive",
                code=400,
            )

        return user

    # ---------------------------------------------------------
    # ASSIGN MEMBER
    # ---------------------------------------------------------

    async def assign_member(
        self,
        team_id: str | PydanticObjectId,
        user_id: str | PydanticObjectId,
        price: int,
        current_user: User,
    ) -> User:

        team = await self._get_active_team(team_id)
        user = await self._get_active_user(user_id)

        # User must not already belong to a team
        if user.team_id is not None:
            raise AppException(
                message="User is already assigned to a team",
                code=400,
            )

        if price < 0:
            raise AppException(
                message="Price cannot be negative",
                code=400,
            )

        # Check team balance
        if team.balance < price:
            raise AppException(
                message="Insufficient team balance",
                code=400,
            )

        balance_before = team.balance
        team.balance -= price

        # Assign user
        user.team_id = team.id
        user.team_price = price

        # Save both
        await self.team_repo.update(team)

        await self.user_repo.update(
            user,
            {
                "team_id": team.id,
                "team_price": price,
            },
        )

        # Wallet ledger
        await TeamWalletTransaction(
            team_id=team.id,
            user_id=user.id,
            transaction_type=WalletTransactionType.PLAYER_ASSIGNMENT,
            amount=-price,
            balance_before=balance_before,
            balance_after=team.balance,
            description=f"Assigned player {user.name}",
            reference_id=str(user.id),
            created_by=current_user.id,
        ).insert()

        return user

    # ---------------------------------------------------------
    # REMOVE MEMBER
    # ---------------------------------------------------------

    async def remove_member(
        self,
        team_id: str | PydanticObjectId,
        user_id: str | PydanticObjectId,
        current_user: User,
    ) -> User:

        team = await self._get_active_team(team_id)
        user = await self._get_active_user(user_id)

        if user.team_id is None or str(user.team_id) != str(team.id):
            raise AppException(
                message="User is not a member of this team",
                code=400,
            )

        refund = user.team_price or 0

        balance_before = team.balance
        team.balance += refund

        # Clear captain / vice captain if necessary
        if team.captain_id and str(team.captain_id) == str(user.id):
            team.captain_id = None

        if team.vice_captain_id and str(team.vice_captain_id) == str(user.id):
            team.vice_captain_id = None

        user.team_id = None
        user.team_price = 0

        await self.team_repo.update(team)

        await self.user_repo.update(
            user,
            {
                "team_id": None,
                "team_price": 0,
            },
        )

        await TeamWalletTransaction(
            team_id=team.id,
            user_id=user.id,
            transaction_type=WalletTransactionType.PLAYER_REMOVAL,
            amount=refund,
            balance_before=balance_before,
            balance_after=team.balance,
            description=f"Removed player {user.name}",
            reference_id=str(user.id),
            created_by=current_user.id,
        ).insert()

        return user

    # ---------------------------------------------------------
    # TRANSFER MEMBER
    # ---------------------------------------------------------

    async def transfer_member(
        self,
        destination_team_id: str | PydanticObjectId,
        user_id: str | PydanticObjectId,
        source_team_id: str | PydanticObjectId,
        price: int | None,
        current_user: User,
    ) -> User:

        source_team = await self._get_active_team(source_team_id)
        destination_team = await self._get_active_team(destination_team_id)
        user = await self._get_active_user(user_id)

        # Same team
        if str(source_team.id) == str(destination_team.id):
            raise AppException(
                message="Source and destination teams must be different",
                code=400,
            )

        # Verify actual membership
        if user.team_id is None or str(user.team_id) != str(source_team.id):
            raise AppException(
                message="User is not a member of the source team",
                code=400,
            )

        old_price = user.team_price or 0
        new_price = old_price if price is None else price

        if new_price < 0:
            raise AppException(
                message="Price cannot be negative",
                code=400,
            )

        # Destination needs the new price
        if destination_team.balance < new_price:
            raise AppException(
                message="Insufficient destination team balance",
                code=400,
            )

        # -----------------------------------------------------
        # Source team refund
        # -----------------------------------------------------

        source_balance_before = source_team.balance
        source_team.balance += old_price

        # -----------------------------------------------------
        # Destination team deduction
        # -----------------------------------------------------

        destination_balance_before = destination_team.balance
        destination_team.balance -= new_price

        # -----------------------------------------------------
        # Captain / vice captain cleanup
        # -----------------------------------------------------

        if source_team.captain_id and str(source_team.captain_id) == str(user.id):
            source_team.captain_id = None

        if source_team.vice_captain_id and str(source_team.vice_captain_id) == str(user.id):
            source_team.vice_captain_id = None

        # -----------------------------------------------------
        # Update user
        # -----------------------------------------------------

        user.team_id = destination_team.id
        user.team_price = new_price

        # -----------------------------------------------------
        # Save
        # -----------------------------------------------------

        await self.team_repo.update(source_team)
        await self.team_repo.update(destination_team)

        await self.user_repo.update(
            user,
            {
                "team_id": destination_team.id,
                "team_price": new_price,
            },
        )

        # -----------------------------------------------------
        # Wallet: source refund
        # -----------------------------------------------------

        await TeamWalletTransaction(
            team_id=source_team.id,
            user_id=user.id,
            transaction_type=WalletTransactionType.PLAYER_TRANSFER_OUT,
            amount=old_price,
            balance_before=source_balance_before,
            balance_after=source_team.balance,
            description=f"Transferred player {user.name} out",
            reference_id=str(destination_team.id),
            created_by=current_user.id,
        ).insert()

        # -----------------------------------------------------
        # Wallet: destination deduction
        # -----------------------------------------------------

        await TeamWalletTransaction(
            team_id=destination_team.id,
            user_id=user.id,
            transaction_type=WalletTransactionType.PLAYER_TRANSFER_IN,
            amount=-new_price,
            balance_before=destination_balance_before,
            balance_after=destination_team.balance,
            description=f"Transferred player {user.name} in",
            reference_id=str(source_team.id),
            created_by=current_user.id,
        ).insert()

        return user

    # ---------------------------------------------------------
    # GET TEAM MEMBERS
    # ---------------------------------------------------------

    async def get_members(
        self,
        team_id: str | PydanticObjectId,
    ) -> list[User]:

        team = await self.team_repo.get_by_id(
            self._object_id(team_id)
        )

        if not team:
            raise AppException(
                message="Team not found",
                code=404,
            )

        return await self.team_repo.get_members(team.id)

    # ---------------------------------------------------------
    # GET USER TEAM
    # ---------------------------------------------------------

    async def get_user_team(
        self,
        user_id: str | PydanticObjectId,
    ) -> Team | None:

        user = await self._get_active_user(user_id)

        if not user.team_id:
            return None

        return await self.team_repo.get_by_id(user.team_id)

    # Backward-compatible aliases for router
    assign_player = assign_member
    remove_player = remove_member
    transfer_player = transfer_member
    get_team_members = get_members

    # ---------------------------------------------------------
    # TEAM CRUD & LEADERSHIP
    # ---------------------------------------------------------

    async def create(
        self,
        data: TeamCreate,
        current_user: User,
    ) -> Team:
        name = self._normalize_name(data.name)
        code = self._normalize_code(data.code)

        existing = await self.team_repo.get_by_code(code)
        if existing:
            raise ConflictException(f"Team with code '{code}' already exists")

        team = Team(
            name=name,
            code=code,
            image_url=data.image_url,
            captain_id=None,
            vice_captain_id=None,
            initial_balance=6250,
            balance=6250,
            is_active=data.is_active,
            created_by=current_user.id,
            updated_by=current_user.id,
        )

        return await self.team_repo.create(team)

    async def get_by_id(
        self,
        team_id: PydanticObjectId,
    ) -> Team:
        team = await self.team_repo.get_by_id(team_id)
        if not team:
            raise NotFoundException("Team not found")
        return team

    async def get_all(
        self,
        active_only: bool = False,
    ) -> list[Team]:
        return await self.team_repo.get_all(active_only=active_only)

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

        if "code" in update_data:
            update_data["code"] = self._normalize_code(update_data["code"])
            existing = await self.team_repo.get_by_code(update_data["code"])
            if existing and existing.id != team.id:
                raise ConflictException(
                    f"Team with code '{update_data['code']}' already exists"
                )

        for field, value in update_data.items():
            setattr(team, field, value)

        team.mark_updated(current_user.id)
        return await self.team_repo.update(team)

    async def update_leadership(
        self,
        team_id: PydanticObjectId,
        captain_id: PydanticObjectId | None,
        vice_captain_id: PydanticObjectId | None,
        vice_captain_price: int = 0,
        current_user_id: PydanticObjectId | None = None,
    ) -> Team:
        team = await self.team_repo.get_by_id(self._object_id(team_id))

        if not team:
            raise NotFoundException("Team not found")

        if not team.is_active:
            raise ConflictException(
                "Cannot update leadership of inactive team"
            )

        if (
            captain_id is not None
            and vice_captain_id is not None
            and str(captain_id) == str(vice_captain_id)
        ):
            raise ConflictException(
                "Captain and vice-captain cannot be the same user"
            )

        # 1. Handle Captain (Direct assignment with 0 M)
        if captain_id is not None:
            captain = await self.user_repo.get_by_id(self._object_id(captain_id))
            if not captain:
                raise NotFoundException("Captain user not found")

            # Check if captain is in another team
            if captain.team_id is not None and str(captain.team_id) != str(team.id):
                raise ConflictException(
                    "Selected captain is already assigned to another squad. Please transfer or remove them first."
                )

            # Auto-join team if not already in team
            if captain.team_id is None:
                captain.team_id = team.id
                captain.team_price = 0
                await self.user_repo.update(
                    captain,
                    {
                        "team_id": team.id,
                        "team_price": 0,
                    },
                )
                await TeamWalletTransaction(
                    team_id=team.id,
                    user_id=captain.id,
                    transaction_type=WalletTransactionType.PLAYER_ASSIGNMENT,
                    amount=0,
                    balance_before=team.balance,
                    balance_after=team.balance,
                    description=f"Direct Captain Assignment: {captain.name}",
                    reference_id=str(captain.id),
                    created_by=current_user_id,
                ).insert()

            team.captain_id = captain.id
        else:
            team.captain_id = None

        # 2. Handle Vice Captain (Custom value assignment)
        if vice_captain_id is not None:
            vice_captain = await self.user_repo.get_by_id(self._object_id(vice_captain_id))
            if not vice_captain:
                raise NotFoundException("Vice-captain user not found")

            if vice_captain.team_id is not None and str(vice_captain.team_id) != str(team.id):
                raise ConflictException(
                    "Selected vice-captain is already assigned to another squad. Please transfer or remove them first."
                )

            vc_price = max(0, int(vice_captain_price or 0))

            # Auto-join team if not already in team
            if vice_captain.team_id is None:
                if team.balance < vc_price:
                    raise ConflictException(
                        f"Insufficient team balance. Team has {team.balance} M, but Vice Captain price is {vc_price} M."
                    )

                balance_before = team.balance
                team.balance -= vc_price
                vice_captain.team_id = team.id
                vice_captain.team_price = vc_price

                await self.user_repo.update(
                    vice_captain,
                    {
                        "team_id": team.id,
                        "team_price": vc_price,
                    },
                )

                await TeamWalletTransaction(
                    team_id=team.id,
                    user_id=vice_captain.id,
                    transaction_type=WalletTransactionType.PLAYER_ASSIGNMENT,
                    amount=-vc_price,
                    balance_before=balance_before,
                    balance_after=team.balance,
                    description=f"Assigned Vice-Captain {vice_captain.name} (Custom price: {vc_price} M)",
                    reference_id=str(vice_captain.id),
                    created_by=current_user_id,
                ).insert()
            else:
                # Already in team: if a new custom price is provided and differs
                old_price = vice_captain.team_price or 0
                if vc_price > 0 and vc_price != old_price:
                    diff = vc_price - old_price
                    if diff > 0 and team.balance < diff:
                        raise ConflictException(
                            f"Insufficient team balance for price adjustment. Need {diff} M more."
                        )
                    balance_before = team.balance
                    team.balance -= diff
                    vice_captain.team_price = vc_price
                    await self.user_repo.update(
                        vice_captain,
                        {"team_price": vc_price},
                    )
                    await TeamWalletTransaction(
                        team_id=team.id,
                        user_id=vice_captain.id,
                        transaction_type=WalletTransactionType.MANUAL_ADJUSTMENT,
                        amount=-diff,
                        balance_before=balance_before,
                        balance_after=team.balance,
                        description=f"Vice-Captain price adjustment for {vice_captain.name}: {old_price} M -> {vc_price} M",
                        reference_id=str(vice_captain.id),
                        created_by=current_user_id,
                    ).insert()

            team.vice_captain_id = vice_captain.id
        else:
            team.vice_captain_id = None

        team.updated_by = current_user_id
        team.updated_at = datetime.now(timezone.utc)

        return await self.team_repo.update(team)

    async def deactivate(
        self,
        team_id: PydanticObjectId,
        current_user: User,
    ) -> Team:
        team = await self.get_by_id(team_id)
        if not team.is_active:
            return team

        users = await self.team_repo.get_members(team.id)

        if users:
            raise ConflictException(
                "Cannot deactivate a team that has players"
            )

        team.is_active = False
        team.mark_updated(current_user.id)
        return await self.team_repo.update(team)

    # ---------------------------------------------------------
    # WALLET & LEDGER
    # ---------------------------------------------------------

    async def get_wallet_summary(
        self,
        team_id: PydanticObjectId,
    ) -> dict:
        team = await self.get_by_id(team_id)
        transactions = await self.wallet_repository.get_by_team(
            team_id, skip=0, limit=1000
        )
        total_tx = await self.wallet_repository.count_by_team(team_id)
        members = await self.team_repo.get_members(team_id)

        total_spent = sum(-t.amount for t in transactions if t.amount < 0)
        total_refunded = sum(t.amount for t in transactions if t.amount > 0)

        return {
            "team_id": str(team.id),
            "team_name": team.name,
            "initial_balance": team.initial_balance,
            "balance": team.balance,
            "total_spent": total_spent,
            "total_refunded": total_refunded,
            "active_players_count": len(members),
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
        await self.team_repo.update(team)

        tx = TeamWalletTransaction(
            team_id=team.id,
            transaction_type=WalletTransactionType.MANUAL_ADJUSTMENT,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description,
            created_by=current_user.id,
        )
        return await self.wallet_repository.create(tx)