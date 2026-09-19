from datetime import datetime, timezone

from beanie import PydanticObjectId

from src.common.exceptions import ConflictException, NotFoundException
from src.modules.team_assignments.model import TeamAssignment
from src.modules.team_assignments.repository import TeamAssignmentRepository
from src.modules.teams.model import Team
from src.modules.teams.wallet_model import TeamWalletTransaction, TransactionType
from src.modules.teams.wallet_repository import TeamWalletRepository
from src.modules.users.model import User


class TeamAssignmentService:

    def __init__(self):
        self.repository = TeamAssignmentRepository()
        self.wallet_repository = TeamWalletRepository()

    async def assign_user(
        self,
        user_id: str,
        team_id: str,
        price: int,
        assigned_by: PydanticObjectId,
    ) -> TeamAssignment:

        # validate IDs
        if not PydanticObjectId.is_valid(user_id):
            raise NotFoundException("Invalid user ID")

        if not PydanticObjectId.is_valid(team_id):
            raise NotFoundException("Invalid team ID")

        if price < 0:
            raise ConflictException("Price must be a non-negative number")

        user_object_id = PydanticObjectId(user_id)
        team_object_id = PydanticObjectId(team_id)

        # get user
        user = await User.get(user_object_id)

        if not user:
            raise NotFoundException("User not found")

        if not user.is_active:
            raise ConflictException("Cannot assign an inactive user")

        if not user.is_allowed:
            raise ConflictException("User is not allowed")

        # get team
        team = await Team.get(team_object_id)

        if not team:
            raise NotFoundException("Team not found")

        if not team.is_active:
            raise ConflictException("Cannot assign user to an inactive team")

        # check existing assignment
        current_assignment = await self.repository.get_current_by_user(
            user_object_id
        )

        if current_assignment:
            if current_assignment.team_id == team_object_id:
                raise ConflictException("User is already assigned to this team")
            raise ConflictException(
                "User is already assigned to another team. Use the transfer feature"
            )

        # check team balance
        if team.balance < price:
            raise ConflictException(
                f"Insufficient team Pushp balance. Required: {price}, Available: {team.balance}"
            )

        # deduct balance and record transaction
        balance_before = team.balance
        balance_after = team.balance - price
        team.balance = balance_after
        team.mark_updated(assigned_by)
        await team.save()

        tx = TeamWalletTransaction(
            team_id=team_object_id,
            transaction_type=TransactionType.ASSIGNMENT,
            amount=-price,
            balance_before=balance_before,
            balance_after=balance_after,
            user_id=user_object_id,
            description=f"Player '{user.name}' assigned with price {price} Pushp",
            created_by=assigned_by,
        )
        await self.wallet_repository.create(tx)

        assignment = TeamAssignment(
            user_id=user_object_id,
            team_id=team_object_id,
            price=price,
            assigned_by=assigned_by,
            is_current=True,
        )

        await self.repository.create(assignment)

        user.team_id = team_object_id
        user.updated_at = datetime.now(timezone.utc)
        await user.save()

        return assignment

    async def transfer_user(
        self,
        user_id: str,
        new_team_id: str,
        price: int | None,
        transferred_by: PydanticObjectId,
    ) -> TeamAssignment:

        if not PydanticObjectId.is_valid(user_id):
            raise NotFoundException("Invalid user ID")

        if not PydanticObjectId.is_valid(new_team_id):
            raise NotFoundException("Invalid team ID")

        user_object_id = PydanticObjectId(user_id)
        new_team_object_id = PydanticObjectId(new_team_id)

        user = await User.get(user_object_id)

        if not user:
            raise NotFoundException("User not found")

        if not user.is_active:
            raise ConflictException("Cannot transfer an inactive user")

        new_team = await Team.get(new_team_object_id)

        if not new_team:
            raise NotFoundException("Destination team not found")

        if not new_team.is_active:
            raise ConflictException("Cannot transfer user to an inactive team")

        current_assignment = await self.repository.get_current_by_user(
            user_object_id
        )

        if not current_assignment:
            raise ConflictException("User is not currently assigned to any team")

        if current_assignment.team_id == new_team_object_id:
            raise ConflictException("User is already assigned to this team")

        old_team = await Team.get(current_assignment.team_id)
        if not old_team:
            raise NotFoundException("Current team not found")

        # Determine price to charge to new team
        price_to_charge = (
            price if price is not None else current_assignment.price
        )

        if price_to_charge < 0:
            raise ConflictException("Price must be a non-negative number")

        # Check new team has sufficient balance
        if new_team.balance < price_to_charge:
            raise ConflictException(
                f"Insufficient balance in new team. Required: {price_to_charge}, Available: {new_team.balance}"
            )

        now = datetime.now(timezone.utc)

        # 1. Old team refund + auto-clear leadership
        old_balance_before = old_team.balance
        old_balance_after = old_team.balance + current_assignment.price
        old_team.balance = old_balance_after

        if old_team.captain_id == user_object_id:
            old_team.captain_id = None

        if old_team.vice_captain_id == user_object_id:
            old_team.vice_captain_id = None

        old_team.mark_updated(transferred_by)
        await old_team.save()

        tx_old = TeamWalletTransaction(
            team_id=old_team.id,
            transaction_type=TransactionType.TRANSFER_OUT,
            amount=current_assignment.price,
            balance_before=old_balance_before,
            balance_after=old_balance_after,
            user_id=user_object_id,
            description=f"Player '{user.name}' transferred to {new_team.name}. Refunded {current_assignment.price} Pushp",
            created_by=transferred_by,
        )
        await self.wallet_repository.create(tx_old)

        # 2. New team deduction
        new_balance_before = new_team.balance
        new_balance_after = new_team.balance - price_to_charge
        new_team.balance = new_balance_after
        new_team.mark_updated(transferred_by)
        await new_team.save()

        tx_new = TeamWalletTransaction(
            team_id=new_team.id,
            transaction_type=TransactionType.TRANSFER_IN,
            amount=-price_to_charge,
            balance_before=new_balance_before,
            balance_after=new_balance_after,
            user_id=user_object_id,
            description=f"Player '{user.name}' transferred from {old_team.name} for {price_to_charge} Pushp",
            created_by=transferred_by,
        )
        await self.wallet_repository.create(tx_new)

        # 3. Update assignment history
        current_assignment.is_current = False
        current_assignment.removed_at = now
        current_assignment.removed_by = transferred_by
        await self.repository.update(current_assignment)

        new_assignment = TeamAssignment(
            user_id=user_object_id,
            team_id=new_team_object_id,
            price=price_to_charge,
            assigned_by=transferred_by,
            assigned_at=now,
            is_current=True,
        )
        await self.repository.create(new_assignment)

        # 4. Update user
        user.team_id = new_team_object_id
        user.updated_at = now
        await user.save()

        return new_assignment

    async def remove_user(
        self,
        user_id: str,
        removed_by: PydanticObjectId,
    ) -> None:

        if not PydanticObjectId.is_valid(user_id):
            raise NotFoundException("Invalid user ID")

        user_object_id = PydanticObjectId(user_id)

        user = await User.get(user_object_id)

        if not user:
            raise NotFoundException("User not found")

        assignment = await self.repository.get_current_by_user(user_object_id)

        if not assignment:
            raise NotFoundException("User is not currently assigned to any team")

        team = await Team.get(assignment.team_id)

        now = datetime.now(timezone.utc)

        # Refund Pushp balance to team and clear leadership if applicable
        if team:
            balance_before = team.balance
            balance_after = team.balance + assignment.price
            team.balance = balance_after

            if team.captain_id == user_object_id:
                team.captain_id = None

            if team.vice_captain_id == user_object_id:
                team.vice_captain_id = None

            team.mark_updated(removed_by)
            await team.save()

            tx = TeamWalletTransaction(
                team_id=team.id,
                transaction_type=TransactionType.REMOVAL,
                amount=assignment.price,
                balance_before=balance_before,
                balance_after=balance_after,
                user_id=user_object_id,
                description=f"Player '{user.name}' removed from team. Refunded {assignment.price} Pushp",
                created_by=removed_by,
            )
            await self.wallet_repository.create(tx)

        assignment.is_current = False
        assignment.removed_at = now
        assignment.removed_by = removed_by

        await self.repository.update(assignment)

        user.team_id = None
        user.updated_at = now

        await user.save()

    async def get_user_team(
        self,
        user_id: str,
    ) -> TeamAssignment:

        if not PydanticObjectId.is_valid(user_id):
            raise NotFoundException("Invalid user ID")

        assignment = await self.repository.get_current_by_user(
            PydanticObjectId(user_id)
        )

        if not assignment:
            raise NotFoundException("User is not assigned to any team")

        return assignment

    async def get_team_members(
        self,
        team_id: str,
    ) -> list[TeamAssignment]:

        if not PydanticObjectId.is_valid(team_id):
            raise NotFoundException("Invalid team ID")

        return await self.repository.get_current_by_team(
            PydanticObjectId(team_id)
        )

    async def get_user_history(
        self,
        user_id: str,
    ) -> list[TeamAssignment]:

        if not PydanticObjectId.is_valid(user_id):
            raise NotFoundException("Invalid user ID")

        return await self.repository.get_history_by_user(
            PydanticObjectId(user_id)
        )