import io
from fastapi.responses import StreamingResponse

from src.common.csv_service import CSVService
from src.common.exceptions import AppException
from src.modules.permissions.model import Permission
from src.modules.permissions.repository import PermissionRepository
from src.modules.permissions.schema import PermissionCreate, PermissionUpdate
from src.modules.users.model import User

class PermissionService:

    def __init__(self):
        self.repo = PermissionRepository()

    async def create(
        self,
        data: PermissionCreate,
        current_user: User,
    ) -> Permission:

        existing = await self.repo.get_by_code(
            data.code
        )

        if existing:
            raise AppException(
                message="Permission code already exists",
                code=409,
            )

        permission = Permission(
            name=data.name,
            code=data.code,
            description=data.description,
            created_by=current_user.id,
            updated_by=current_user.id,
        )

        return await self.repo.create(permission)

    async def get_by_id(
        self,
        permission_id: str,
    ) -> Permission:

        permission = await self.repo.get_by_id(
            permission_id
        )

        if not permission:
            raise AppException(
                message="Permission not found",
                code=404,
            )

        return permission

    async def get_all(self) -> list[Permission]:

        return await self.repo.get_all()

    async def update(
        self,
        permission_id: str,
        data: PermissionUpdate,
        current_user: User,
    ) -> Permission:

        permission = await self.get_by_id(
            permission_id
        )

        update_data = data.model_dump(
            exclude_unset=True
        )

        if "code" in update_data:

            existing = await self.repo.get_by_code(
                update_data["code"]
            )

            if existing and str(existing.id) != permission_id:
                raise AppException(
                    message="Permission code already exists",
                    code=409,
                )

        for field, value in update_data.items():
            setattr(permission, field, value)

        permission.mark_updated(current_user.id)

        return await self.repo.update(permission)

    async def delete(
        self,
        permission_id: str,
    ) -> None:

        permission = await self.get_by_id(
            permission_id
        )

        await self.repo.delete(permission)

    async def export_csv(self) -> StreamingResponse:
        permissions = await self.repo.get_all()
        rows = []
        for p in permissions:
            rows.append({
                "name": p.name or "",
                "code": p.code or "",
                "description": p.description or "",
                "is_active": "true" if p.is_active else "false",
            })

        columns = ["name", "code", "description", "is_active"]
        csv_bytes = CSVService.generate(rows, columns)

        return StreamingResponse(
            io.BytesIO(csv_bytes),
            media_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="permissions_export.csv"'
            },
        )

    async def import_csv(
        self,
        file_content: bytes,
        current_user: User,
    ) -> dict:
        try:
            columns, rows = CSVService.read(file_content)
        except Exception as e:
            raise AppException(message=f"Failed to parse CSV: {str(e)}", code=400)

        CSVService.validate_columns(columns, {"code", "name"})

        total_rows = len(rows)
        created_count = 0
        updated_count = 0
        failed_count = 0
        created_items: list[str] = []
        updated_items: list[str] = []
        errors: list[dict] = []

        for idx, row in enumerate(rows, start=2):
            code = (row.get("code") or "").strip()
            name = (row.get("name") or "").strip()
            description = (row.get("description") or "").strip() or None
            is_active_val = (row.get("is_active") or "true").strip().lower()
            is_active = is_active_val not in ("false", "0", "no", "inactive")

            if not code or not name:
                failed_count += 1
                errors.append({
                    "row": idx,
                    "error": "Both 'name' and 'code' are required."
                })
                continue

            existing = await self.repo.get_by_code(code)
            if existing:
                existing.name = name
                if description is not None:
                    existing.description = description
                existing.is_active = is_active
                existing.mark_updated(current_user.id)
                await self.repo.update(existing)
                updated_count += 1
                updated_items.append(f"{code} ({name})")
            else:
                new_perm = Permission(
                    name=name,
                    code=code,
                    description=description,
                    is_active=is_active,
                    created_by=current_user.id,
                    updated_by=current_user.id,
                )
                await self.repo.create(new_perm)
                created_count += 1
                created_items.append(f"{code} ({name})")

        return {
            "total_rows": total_rows,
            "created_count": created_count,
            "updated_count": updated_count,
            "failed_count": failed_count,
            "created_items": created_items,
            "updated_items": updated_items,
            "errors": errors,
        }