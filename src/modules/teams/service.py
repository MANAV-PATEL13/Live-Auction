import csv
import io
from datetime import datetime, timezone
from beanie import PydanticObjectId
from fastapi.responses import StreamingResponse

from src.common.exceptions import AppException, ConflictException, NotFoundException
from src.modules.teams.model import Team
from src.modules.teams.repository import TeamRepository
from src.modules.teams.schema import TeamCreate, TeamResponse, TeamUpdate, TeamImportSummary, TeamImportReport
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

        # Check squad limit (Max 11 players)
        current_members = await User.find(User.team_id == team.id).count()
        if current_members >= 11:
            raise AppException(
                message=f"Team squad is full ({current_members}/11 players). Maximum 11 players allowed per team.",
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

        # Check destination team squad limit (Max 11 players)
        dest_members_count = await User.find(User.team_id == destination_team.id).count()
        if dest_members_count >= 11:
            raise AppException(
                message=f"Destination team squad is full ({dest_members_count}/11 players). Maximum 11 players allowed per team.",
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
                message=f"Insufficient destination team balance ({destination_team.balance} M available, {new_price} M required)",
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
            description=f"Player {user.name} transferred to {destination_team.name}. Refunded {old_price} M",
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
            description=f"Player {user.name} transferred from {source_team.name} for {new_price} M",
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

    async def get_all_with_counts(
        self,
        active_only: bool = False,
    ) -> list[TeamResponse]:
        teams = await self.team_repo.get_all(active_only=active_only)
        
        count_map: dict[str, set[str]] = {}
        try:
            users_with_team = await User.find(User.team_id != None).to_list()
            for u in users_with_team:
                if u.team_id:
                    tid = str(u.team_id)
                    if tid not in count_map:
                        count_map[tid] = set()
                    count_map[tid].add(str(u.id))
        except Exception as e:
            print(f"[TeamService] Error aggregating users by team_id: {e}")

        result: list[TeamResponse] = []
        for team in teams:
            t_dict = team.model_dump()
            t_id = str(team.id)
            
            squad_ids = set(count_map.get(t_id, set()))
            if team.captain_id:
                squad_ids.add(str(team.captain_id))
            if team.vice_captain_id:
                squad_ids.add(str(team.vice_captain_id))
                
            c = len(squad_ids)
            t_dict["id"] = t_id
            t_dict["member_count"] = c
            t_dict["members_count"] = c
            t_dict["player_count"] = c
            t_dict["players_count"] = c
            result.append(TeamResponse(**t_dict))
        return result

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

    # ---------------------------------------------------------
    # CSV IMPORT & EXPORT
    # ---------------------------------------------------------

    async def import_csv(
        self,
        file_content: bytes,
        current_user_id: PydanticObjectId | None = None,
    ) -> TeamImportSummary:
        try:
            content = file_content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise AppException(
                message="CSV file must be UTF-8 encoded",
                code=400,
            )

        reader = csv.DictReader(io.StringIO(content))
        if not reader.fieldnames:
            raise AppException(
                message="CSV file is empty or has no header",
                code=400,
            )

        # Normalize field names (case-insensitive, trimmed)
        field_map = {}
        for fn in reader.fieldnames:
            if not fn:
                continue
            normalized_key = fn.strip().lower().replace(" ", "_")
            field_map[normalized_key] = fn

        # Ensure required fields (name, code)
        if "name" not in field_map or "code" not in field_map:
            raise AppException(
                message="CSV must contain 'name' and 'code' columns",
                code=400,
            )

        total_rows = 0
        created_count = 0
        updated_count = 0
        failed_count = 0
        reports: list[TeamImportReport] = []

        for idx, raw_row in enumerate(reader, start=2):
            total_rows += 1

            name_val = raw_row.get(field_map.get("name", "name"))
            code_val = raw_row.get(field_map.get("code", "code"))

            # Check image_url variants
            img_key = field_map.get("image_url") or field_map.get("image") or field_map.get("logo")
            img_val = raw_row.get(img_key) if img_key else None

            # Check captain variants (captain, captian, captain_roll_no, etc.)
            cap_key = (
                field_map.get("captain")
                or field_map.get("captian")
                or field_map.get("captain_roll_no")
                or field_map.get("captain_email")
            )
            cap_val = raw_row.get(cap_key) if cap_key else None

            name = name_val.strip() if name_val else ""
            code = code_val.strip().upper() if code_val else ""
            image_url = img_val.strip() if img_val else None
            captain_str = cap_val.strip() if cap_val else None

            if not name:
                failed_count += 1
                reports.append(
                    TeamImportReport(
                        row_number=idx,
                        name=name,
                        code=code,
                        status="FAILED",
                        reason="Team name is required",
                    )
                )
                continue

            if not code:
                failed_count += 1
                reports.append(
                    TeamImportReport(
                        row_number=idx,
                        name=name,
                        code=code,
                        status="FAILED",
                        reason="Team code is required",
                    )
                )
                continue

            # Resolve captain user if provided
            captain_user: User | None = None
            if captain_str:
                # 1. Search by roll_no
                captain_user = await User.find_one(
                    User.roll_no == captain_str,
                    User.is_active == True,
                )
                # 2. Search by email
                if not captain_user:
                    captain_user = await User.find_one(
                        User.email == captain_str.lower(),
                        User.is_active == True,
                    )
                # 3. Search by PydanticObjectId if valid
                if not captain_user and PydanticObjectId.is_valid(captain_str):
                    captain_user = await User.find_one(
                        User.id == PydanticObjectId(captain_str),
                        User.is_active == True,
                    )

            try:
                # Check if team exists by code (unique)
                existing_team = await Team.find_one(Team.code == code)

                if existing_team:
                    # Update existing team
                    existing_team.name = name
                    if image_url is not None:
                        existing_team.image_url = image_url
                    if captain_user:
                        existing_team.captain_id = captain_user.id
                    if current_user_id:
                        existing_team.mark_updated(current_user_id)
                    await self.team_repo.update(existing_team)

                    # Assign captain to this team
                    if captain_user:
                        captain_user.team_id = existing_team.id
                        captain_user.team_name = existing_team.name
                        if captain_user.team_price is None:
                            captain_user.team_price = 0
                        await captain_user.save()

                    updated_count += 1
                    reports.append(
                        TeamImportReport(
                            row_number=idx,
                            name=name,
                            code=code,
                            status="UPDATED",
                        )
                    )
                else:
                    # Create new team
                    new_team = Team(
                        name=name,
                        code=code,
                        image_url=image_url,
                        captain_id=captain_user.id if captain_user else None,
                        initial_balance=6250,
                        balance=6250,
                        is_active=True,
                    )
                    if current_user_id:
                        new_team.mark_created(current_user_id)
                    created_team = await self.team_repo.create(new_team)

                    # Assign captain to this team
                    if captain_user and created_team:
                        captain_user.team_id = created_team.id
                        captain_user.team_name = created_team.name
                        if captain_user.team_price is None:
                            captain_user.team_price = 0
                        await captain_user.save()

                    created_count += 1
                    reports.append(
                        TeamImportReport(
                            row_number=idx,
                            name=name,
                            code=code,
                            status="CREATED",
                        )
                    )
            except Exception as ex:
                failed_count += 1
                reports.append(
                    TeamImportReport(
                        row_number=idx,
                        name=name,
                        code=code,
                        status="FAILED",
                        reason=str(ex),
                    )
                )

        return TeamImportSummary(
            total_rows=total_rows,
            created_count=created_count,
            updated_count=updated_count,
            failed_count=failed_count,
            reports=reports,
        )

    async def export_csv(self) -> StreamingResponse:
        teams = await Team.find(Team.is_active == True).sort("+code").to_list()

        # Collect captain IDs
        captain_ids = [t.captain_id for t in teams if t.captain_id]
        captains = {}
        if captain_ids:
            cap_users = await User.find({"_id": {"$in": captain_ids}}).to_list()
            captains = {u.id: u for u in cap_users}

        output = io.StringIO(newline="")
        writer = csv.writer(output)

        # Write exact canonical header
        writer.writerow(["name", "code", "image_url", "captain"])

        for t in teams:
            cap_u = captains.get(t.captain_id) if t.captain_id else None
            # Use roll_no if available, else email or name
            cap_ident = ""
            if cap_u:
                cap_ident = cap_u.roll_no or cap_u.email or f"{cap_u.first_name} {cap_u.last_name}".strip()

            writer.writerow([
                t.name or "",
                t.code or "",
                t.image_url or "",
                cap_ident,
            ])

        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            media_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="teams_export.csv"',
            },
        )