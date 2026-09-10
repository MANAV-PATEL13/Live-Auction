from datetime import datetime, timezone
from beanie import PydanticObjectId
from src.core.database_transaction import mongo_transaction

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
            initial_balance=6250,
            balance=6250,
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

        for field, value in update_data.items():
            setattr(team, field, value)

        team.mark_updated(current_user.id)
        return await self.repository.update(team)

    async def update_leadership(
        self,
        team_id: PydanticObjectId,
        captain_id: PydanticObjectId | None,
        vice_captain_id: PydanticObjectId | None,
        current_user_id: PydanticObjectId,
    ) -> Team:
        team = await self.repository.get_by_id(team_id)

        if not team:
            raise NotFoundException("team not found")

        if not team.is_active:
            raise ConflictException(
                "cannot update leadership of inactive team"
            )

        # --------------------------------------------------
        # Captain and vice-captain cannot be the same person
        # --------------------------------------------------
        if (
            captain_id is not None
            and vice_captain_id is not None
            and captain_id == vice_captain_id
        ):
            raise ConflictException(
                "captain and vice-captain cannot be the same user"
            )

        # --------------------------------------------------
        # Validate captain membership
        # --------------------------------------------------
        if captain_id is not None:
            captain = await self.user_repository.get_by_id(captain_id)
            if not captain:
                raise NotFoundException("captain user not found")
            if captain.team_id != team.id:
                raise ConflictException("captain must be a member of this team")

        # --------------------------------------------------
        # Validate vice-captain membership
        # --------------------------------------------------
        if vice_captain_id is not None:
            vice_captain = await self.user_repository.get_by_id(vice_captain_id)
            if not vice_captain:
                raise NotFoundException("vice-captain user not found")
            if vice_captain.team_id != team.id:
                raise ConflictException("vice-captain must be a member of this team")

        # --------------------------------------------------
        # Update
        # --------------------------------------------------
        team.captain_id = captain_id
        team.vice_captain_id = vice_captain_id
        team.updated_by = current_user_id
        team.updated_at = datetime.now(timezone.utc)

        return await self.repository.update(team)

    async def deactivate(
        self,
        team_id: PydanticObjectId,
        current_user: User,
    ) -> Team:
        team = await self.get_by_id(team_id)
        if not team.is_active:
            return team

        users = await User.find(
            User.team_id == team.id
        ).to_list()

        if users:
            raise ConflictException(
                "cannot deactivate a team that has players"
            )

        team.is_active = False
        team.mark_updated(current_user.id)
        return await self.repository.update(team)

    async def assign_player(
        self,
        team_id: PydanticObjectId,
        user_id: PydanticObjectId,
        price: int,
        current_user_id: PydanticObjectId,
    ) -> User:
        async with mongo_transaction() as session:
            team = await Team.get(team_id, session=session)
            if not team:
                raise NotFoundException("Team not found")
            if not team.is_active:
                raise ConflictException("Cannot assign player to inactive team")

            user = await User.get(user_id, session=session)
            if not user:
                raise NotFoundException("User not found")
            if not user.is_active:
                raise ConflictException("Cannot assign inactive user")

            if user.team_id is not None:
                raise ConflictException("User already belongs to a team")

            if team.balance < price:
                raise ConflictException(
                    f"Insufficient Pushp balance. Available: {team.balance}, required: {price}"
                )

            balance_before = team.balance
            balance_after = balance_before - price
            now = datetime.now(timezone.utc)

            team.balance = balance_after
            team.updated_by = current_user_id
            team.updated_at = now
            await team.save(session=session)

            user.team_id = team.id
            user.team_price = price
            user.updated_at = now
            await user.save(session=session)

            transaction = TeamWalletTransaction(
                team_id=team.id,
                user_id=user.id,
                transaction_type=TransactionType.ASSIGNMENT,
                amount=-price,
                balance_before=balance_before,
                balance_after=balance_after,
                description=f"Player assigned to team: {user.name}",
                created_by=current_user_id,
                created_at=now,
            )
            await transaction.insert(session=session)

            return user

    async def remove_player(
        self,
        team_id: PydanticObjectId,
        user_id: PydanticObjectId,
        current_user_id: PydanticObjectId,
    ) -> User:
        async with mongo_transaction() as session:
            team = await Team.get(team_id, session=session)
            if not team:
                raise NotFoundException("Team not found")

            user = await User.get(user_id, session=session)
            if not user:
                raise NotFoundException("User not found")

            if user.team_id != team.id:
                raise ConflictException("User does not belong to this team")

            price = user.team_price
            balance_before = team.balance
            balance_after = balance_before + price
            now = datetime.now(timezone.utc)

            team.balance = balance_after
            team.updated_by = current_user_id
            team.updated_at = now

            if team.captain_id == user.id:
                team.captain_id = None
            if team.vice_captain_id == user.id:
                team.vice_captain_id = None

            await team.save(session=session)

            user.team_id = None
            user.team_price = 0
            user.updated_at = now

            await user.save(session=session)

            transaction = TeamWalletTransaction(
                team_id=team.id,
                user_id=user.id,
                transaction_type=TransactionType.REMOVAL,
                amount=price,
                balance_before=balance_before,
                balance_after=balance_after,
                description=f"Player removed from team: {user.name}",
                created_by=current_user_id,
                created_at=now,
            )
            await transaction.insert(session=session)

            return user

    async def transfer_player(
        self,
        source_team_id: PydanticObjectId,
        user_id: PydanticObjectId,
        destination_team_id: PydanticObjectId,
        current_user_id: PydanticObjectId,
        new_price: int | None = None,
    ) -> User:
        async with mongo_transaction() as session:
            source_team = await Team.get(source_team_id, session=session)
            if not source_team:
                raise NotFoundException("source team not found")

            destination_team = await Team.get(destination_team_id, session=session)
            if not destination_team:
                raise NotFoundException("destination team not found")
            if not destination_team.is_active:
                raise ConflictException("cannot transfer player to inactive team")

            if source_team.id == destination_team.id:
                raise ConflictException("source and destination teams must be different")

            user = await User.get(user_id, session=session)
            if not user:
                raise NotFoundException("user not found")

            if user.team_id != source_team.id:
                raise ConflictException("user does not belong to source team")

            old_price = user.team_price
            price = old_price if new_price is None else new_price

            source_balance_before = source_team.balance
            source_balance_after = source_balance_before + old_price

            destination_balance_before = destination_team.balance
            if destination_balance_before < price:
                raise ConflictException(
                    f"insufficient Pushp balance in destination team. available: {destination_balance_before}, required: {price}"
                )
            destination_balance_after = destination_balance_before - price

            now = datetime.now(timezone.utc)

            source_team.balance = source_balance_after
            source_team.updated_by = current_user_id
            source_team.updated_at = now

            if source_team.captain_id == user.id:
                source_team.captain_id = None
            if source_team.vice_captain_id == user.id:
                source_team.vice_captain_id = None

            await source_team.save(session=session)

            destination_team.balance = destination_balance_after
            destination_team.updated_by = current_user_id
            destination_team.updated_at = now

            await destination_team.save(session=session)

            user.team_id = destination_team.id
            user.team_price = price
            user.updated_at = now

            await user.save(session=session)

            source_transaction = TeamWalletTransaction(
                team_id=source_team.id,
                user_id=user.id,
                transaction_type=TransactionType.TRANSFER_OUT,
                amount=old_price,
                balance_before=source_balance_before,
                balance_after=source_balance_after,
                description=f"Player transferred to team {destination_team.name}",
                created_by=current_user_id,
                created_at=now,
            )
            await source_transaction.insert(session=session)

            destination_transaction = TeamWalletTransaction(
                team_id=destination_team.id,
                user_id=user.id,
                transaction_type=TransactionType.TRANSFER_IN,
                amount=-price,
                balance_before=destination_balance_before,
                balance_after=destination_balance_after,
                description=f"Player transferred from team {source_team.name}",
                created_by=current_user_id,
                created_at=now,
            )
            await destination_transaction.insert(session=session)

            return user

    async def get_team_members(
        self,
        team_id: PydanticObjectId,
    ) -> list[User]:
        team = await self.repository.get_by_id(team_id)

        if not team:
            raise NotFoundException("team not found")

        return await self.user_repository.get_by_team_id(team_id)

    async def get_user_team(
        self,
        user_id: PydanticObjectId,
    ) -> Team | None:
        user = await self.user_repository.get_by_id(user_id)

        if not user:
            raise NotFoundException("user not found")

        if user.team_id is None:
            return None

        return await self.repository.get_by_id(user.team_id)

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