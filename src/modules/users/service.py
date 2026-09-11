import csv
import io

from fastapi.responses import StreamingResponse

from beanie import PydanticObjectId

from src.modules.users.model import User
from src.modules.users.schema import UserCreate, UserUpdate, UserGroupsUpdate, ChangePasswordRequest
from src.modules.users.repository import UserRepository
from src.core.security import hash_password, verify_password
from src.common.exceptions import EmailAreadyExistsException, NotFoundException, AppException, InvalidCredentialsException

from pydantic import ValidationError
from src.modules.users.csv_schema import UserCSVRow, UserImportRowReport, UserImportSummary, UserBasePriceImportSummary
from src.modules.users.csv_service import UserCSVService

class UserService:

    def __init__(self):
        self.repo = UserRepository()


    async def create_user(
            self,
            data : UserCreate,
    ):

        email = str(data.email).lower().strip()

        existing_user = await self.repo.get_by_email(
            email
        )

        if existing_user:
            raise EmailAreadyExistsException()

        name_parts = [
            data.first_name.strip(),
            data.middle_name.strip() if data.middle_name else None,
            data.last_name.strip()
        ]

        name = " ".join(
            part for part in name_parts
            if part
        )

        roll_no = (
            data.roll_no.strip()
            if data.roll_no
            else None
        )

        mobile = (
            data.mobile.strip()
            if data.mobile
            else None
        )

        image_url = (
            data.image_url.strip()
            if data.image_url
            else None
        )


        user = User(
            name = name,
            first_name= data.first_name.strip(),
            middle_name=(
                data.middle_name.strip()
                if data.middle_name
                else None
            ),
            last_name=data.last_name.strip(),
            roll_no=roll_no,
            email=email,
            mobile=mobile,
            image_url=image_url,
            password_hash=hash_password(data.password),

        )

        return await self.repo.create(user)

    async def get_by_id(
            self,
            user_id: str,
    ) -> User:

        user = await self.repo.get_by_id(user_id)

        if not user:
            raise NotFoundException("User not found")

        return user

    async def get_all(self) -> list[User]:
        return await self.repo.get_all()


    async def assign_team(
        self,
        user_id: str,
        team_id: PydanticObjectId | None,
    ) -> User:

        user = await self.get_by_id(user_id)

        return await self.repo.update(
            user,
            {
                "team_id": team_id,
            },
        )

    async def get_user_team(
        self,
        user_id: str,
    ):
        from src.modules.teams.service import TeamService
        return await TeamService().get_user_team(user_id)


    async def update(
            self,
            user_id : str,
            data : UserUpdate
    ) -> User:

        user = await self.get_by_id(user_id)

        update_data = data.model_dump(
            exclude_unset=True
        )

        if "first_name" in update_data:
            update_data["first_name"] = (
                update_data["first_name"].strip()
            )

        if "middle_name" in update_data:
            update_data["middle_name"] = (
                update_data["middle_name"].strip()
                if update_data["middle_name"]
                else None
            )

        if "last_name" in update_data:
            update_data["last_name"] = (
                update_data["last_name"].strip()
            )

        if "image_url" in update_data:
            update_data["image_url"] = (
                update_data["image_url"].strip()
                if update_data["image_url"]
                else None
            )

        if "email" in update_data:
            update_data["email"] = (
                str(update_data["email"]).lower().strip()
            )

            existing = await self.repo.get_by_email(
                update_data["email"]
            )

            if existing and existing.id != user.id:
                raise EmailAreadyExistsException()

        # Rebuild display name
        first_name = update_data.get(
            "first_name",
            user.first_name,
        )

        middle_name = update_data.get(
            "middle_name",
            user.middle_name,
        )

        last_name = update_data.get(
            "last_name",
            user.last_name,
        )

        update_data["name"] = " ".join(
            part
            for part in [
                first_name,
                middle_name,
                last_name,
            ]
            if part
        )

        return await self.repo.update(
            user,
            update_data,
        )


    async def reset_password(
            self,
            user_id : str | PydanticObjectId,
    ) -> User:
        """Admin resets a user's password to the default (roll_no@321)."""

        user = await self.repo.get_by_id(user_id)

        if not user:
            raise NotFoundException(
                "User not found"
            )

        default_password = (
            f"{user.roll_no}@321"
            if user.roll_no
            else f"{str(user.id)}@321"
        )

        return await self.repo.update(
            user,
            {"password_hash": hash_password(default_password)},
        )

    async def change_password(
            self,
            user_id: str | PydanticObjectId,
            data: "ChangePasswordRequest",
    ) -> User:
        """User changes their own password after verifying the current one."""

        user = await self.repo.get_by_id(user_id)

        if not user:
            raise NotFoundException("User not found")

        if not verify_password(data.current_password, user.password_hash):
            raise InvalidCredentialsException()

        return await self.repo.update(
            user,
            {"password_hash": hash_password(data.new_password)},
        )

    async def update_groups(
            self,
            user_id: str,
            data: UserGroupsUpdate,
    ) -> User:

        user = await self.get_by_id(user_id)

        return await self.repo.update(
            user,
            {"group_ids": data.group_ids},
        )

    async def reactivate(
            self,
            user_id: str,
    ) -> User:

        user = await self.get_by_id(user_id)

        return await self.repo.update(
            user,
            {"is_allowed": True},
        )
    
    async def deactivate(
            self,
            user_id: str,
    ) -> User:

        user = await self.get_by_id(user_id)

        return await self.repo.update(
            user,
            {"is_allowed": False},
        )

    async def delete(
            self,
            user_id: str,
    ) -> None:

        user = await self.get_by_id(user_id)

        await self.repo.update(
            user,
            {"is_active": False},
        )

    async def import_csv(
            self,
            file_content : bytes
    ) -> UserImportSummary:

        try:
            content = file_content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise AppException(
                message="CSV file must be UTF-8 encoded",
                code=400
            )

        reader = csv.DictReader(
            io.StringIO(content)
        )

        if not reader.fieldnames:
            raise AppException(
                message="CSV file is empty or has no header",
                code=400
            )

        required_columns = {
            "first_name",
            "last_name",
            "roll_no",
            "email"
        }

        columns = {
            column.strip()
            for column in reader.fieldnames
            if column
        }

        missing_columns = (
            required_columns - columns
        )

        if missing_columns:
            raise AppException(
                message=(
                    "Missing required columns: "
                    + ", ".join(sorted(missing_columns))
                ),
                code=400,
            )

        rows = list(reader)

        total_rows = len(rows)

        created = 0
        failed = 0

        report : list[UserImportRowReport] = []

        csv_emails : set[str] = set()
        csv_roll_numbers : set[str] = set()

        for row_number, raw_row in enumerate(
            rows,
            start=2,
        ):

            try:

                row_data = {
                    key : (
                        value.strip()
                        if isinstance(value, str)
                        else value
                    )
                    for key, value in raw_row.items()
                    if key
                }

                row = UserCSVRow(
                    **row_data
                )

            except ValidationError as exc:

                reasons = []

                for error in exc.errors():

                    field = ".".join(
                        str(value)
                        for value in error["loc"]
                    )

                    reasons.append(
                        f"{field}: {error['msg']}"
                    )

                failed += 1

                report.append(
                    UserImportRowReport(
                        row=row_number,
                        status="failed",
                        reason="; ".join(reasons),
                    )
                )

                continue

            email = str(row.email).lower().strip()
            roll_no = row.roll_no.strip()

            if email in csv_emails:

                failed += 1

                report.append(
                    UserImportRowReport(
                        row=row_number,
                        status="failed",
                        reason="Duplicate email in CSV"
                    )
                )

                continue

            if roll_no in csv_roll_numbers:

                failed += 1

                report.append(
                    UserImportRowReport(
                        row=row_number,
                        status="failed",
                        reason="Duplicate roll number in CSV"
                    )
                )

                continue

            csv_emails.add(email)
            csv_roll_numbers.add(roll_no)


            # Check existing database user
            existing_email = await self.repo.get_by_email(
                email
            )

            if existing_email:

                failed += 1

                report.append(
                    UserImportRowReport(
                        row=row_number,
                        status="failed",
                        reason="Email already exists",
                    )
                )

                continue

            # Check roll number
            existing_roll = await User.find_one(
                User.roll_no == roll_no
            )

            if existing_roll:

                failed += 1

                report.append(
                    UserImportRowReport(
                        row=row_number,
                        status="failed",
                        reason="Roll number already exists",
                    )
                )

                continue

        
            name_parts = [
                row.first_name.strip(),
                (
                    row.middle_name.strip()
                    if row.middle_name
                    else None
                ),
                row.last_name.strip(),
            ]

            name = " ".join(
                part
                for part in name_parts
                if part
            )

            password = f"{roll_no}@321"

            user = User(
                name=name,
                first_name=row.first_name.strip(),
                middle_name=(
                    row.middle_name.strip()
                    if row.middle_name
                    else None
                ),
                last_name=row.last_name.strip(),
                roll_no=roll_no,
                email=email,
                mobile=(
                    row.mobile.strip()
                    if row.mobile
                    else None
                ),
                image_url=(
                    row.image_url.strip()
                    if row.image_url
                    else None
                ),
                password_hash=hash_password(
                    password
                ),
            )

            try:

                await self.repo.create(user)

                created += 1

                report.append(
                    UserImportRowReport(
                        row=row_number,
                        status="created",
                    )
                )

            except Exception as exc:

                failed += 1

                report.append(
                    UserImportRowReport(
                        row=row_number,
                        status="failed",
                        reason=str(exc),
                    )
                )

        return UserImportSummary(
            total_rows=total_rows,
            created=created,
            failed=failed,
            report=report,
        )


    async def export_csv(self) -> StreamingResponse:

        users = await self.repo.get_all()

        output = io.StringIO()

        writer = csv.writer(output)

        writer.writerow([
            "id",
            "name",
            "first_name",
            "middle_name",
            "last_name",
            "roll_no",
            "email",
            "mobile",
            "image_url",
            "group_ids",
            "team_id",
            "is_active",
            "is_allowed",
            "is_superuser",
            "created_at",
            "updated_at",
        ])

        for user in users:

            writer.writerow([
                str(user.id),
                user.name,
                user.first_name,
                user.middle_name or "",
                user.last_name,
                user.roll_no or "",
                str(user.email),
                user.mobile or "",
                user.image_url or "",
                ",".join(
                    str(group_id)
                    for group_id in user.group_ids
                ),
                str(user.team_id)
                if user.team_id
                else "",
                user.is_active,
                user.is_allowed,
                user.is_superuser,
                user.created_at.isoformat(),
                user.updated_at.isoformat(),
            ])

        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition":
                    'attachment; filename="users_export.csv"'
            },
        )

    async def import_base_prices(
        self,
        file_content: bytes,
    ) -> UserBasePriceImportSummary:

        valid_rows, failed_rows = (
            UserCSVService.parse_base_price(
                file_content
            )
        )

        report = failed_rows.copy()

        updated = 0
        failed = len(failed_rows)

        for row_number, row in valid_rows:

            users = await User.find(
                User.roll_no == row.roll_no
            ).to_list()

            if not users:

                failed += 1

                report.append(
                    UserImportRowReport(
                        row=row_number,
                        status="failed",
                        reason="User not found",
                    )
                )

                continue

            if len(users) > 1:

                failed += 1

                report.append(
                    UserImportRowReport(
                        row=row_number,
                        status="failed",
                        reason=(
                            "Multiple users found "
                            "with this roll number"
                        ),
                    )
                )

                continue

            user = users[0]

            if not user.is_registered:

                failed += 1

                report.append(
                    UserImportRowReport(
                        row=row_number,
                        status="failed",
                        reason=(
                            "User is not registered "
                            "for participation"
                        ),
                    )
                )

                continue

            await self.repo.update(
                user,
                {
                    "base_price": row.base_price,
                },
            )

            updated += 1

            report.append(
                UserImportRowReport(
                    row=row_number,
                    status="updated",
                    reason=(
                        f"Base price updated to "
                        f"{row.base_price}"
                    ),
                )
            )

        return UserBasePriceImportSummary(
            total_rows=len(valid_rows) + len(failed_rows),
            updated=updated,
            failed=failed,
            report=report,
        )