import io
from datetime import datetime, timezone
from typing import Any
from beanie import PydanticObjectId
from fastapi.responses import StreamingResponse

from src.common.exceptions import AppException
from src.modules.permission_groups.model import PermissionGroup
from src.modules.permission_groups.repository import (
    PermissionGroupRepository,
)
from src.modules.permission_groups.schema import (
    PermissionGroupCreate,
    PermissionGroupUpdate,
)
from src.modules.permissions.repository import (
    PermissionRepository,
)
from src.modules.users.model import User


class PermissionGroupService:

    def __init__(self):
        self.repo = PermissionGroupRepository()
        self.permission_repo = PermissionRepository()

    def _serialize_group(self, group: PermissionGroup, user_count: int = 0) -> dict[str, Any]:
        gid = str(group.id)
        raw_pids = getattr(group, "permission_ids", []) or getattr(group, "permissions", []) or []
        return {
            "id": gid,
            "_id": gid,
            "name": group.name,
            "description": group.description or "",
            "permission_ids": [str(pid) for pid in raw_pids],
            "permissions": [str(pid) for pid in raw_pids],
            "is_active": group.is_active,
            "user_count": user_count,
            "created_at": group.created_at.isoformat() if getattr(group, "created_at", None) else None,
            "updated_at": group.updated_at.isoformat() if getattr(group, "updated_at", None) else None,
        }

    async def _get_group_doc(self, group_id: str) -> PermissionGroup:
        group = await self.repo.get_by_id(group_id)
        if not group:
            raise AppException(
                message="Permission group not found",
                code=404,
            )
        return group

    async def _validate_permissions(
        self,
        permission_ids: list[str],
    ) -> None:
        for permission_id in permission_ids:
            permission = await self.permission_repo.get_by_id(permission_id)
            if not permission:
                raise AppException(
                    message=f"Permission not found: {permission_id}",
                    code=404,
                )

    async def create(
        self,
        data: PermissionGroupCreate,
        current_user: User,
    ) -> dict[str, Any]:
        existing = await self.repo.get_by_name(data.name)
        if existing:
            raise AppException(
                message="Permission group already exists",
                code=409,
            )

        await self._validate_permissions(data.permission_ids)

        group = PermissionGroup(
            name=data.name,
            description=data.description,
            permission_ids=data.permission_ids,
            created_by=current_user.id,
            updated_by=current_user.id,
        )

        created = await self.repo.create(group)
        return self._serialize_group(created, 0)

    async def get_by_id(
        self,
        group_id: str,
    ) -> dict[str, Any]:
        group = await self._get_group_doc(group_id)
        gid = str(group.id)
        user_count = await User.find({"group_ids": gid}).count()
        return self._serialize_group(group, user_count)

    async def get_all(
        self,
    ) -> list[dict[str, Any]]:
        groups = await self.repo.get_all()
        result = []
        for g in groups:
            gid = str(g.id)
            user_count = await User.find({"group_ids": gid}).count()
            result.append(self._serialize_group(g, user_count))
        return result

    async def get_group_users(self, group_id: str) -> list[dict[str, Any]]:
        await self._get_group_doc(group_id)
        users = await User.find({"group_ids": group_id}).to_list()
        return [
            {
                "id": str(u.id),
                "name": u.name,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "roll_no": u.roll_no,
                "email": u.email,
                "mobile": u.mobile,
                "is_active": u.is_active,
                "is_allowed": u.is_allowed,
                "group_ids": u.group_ids,
            }
            for u in users
        ]

    async def assign_users(self, group_id: str, user_ids: list[str]) -> dict[str, Any]:
        await self._get_group_doc(group_id)
        target_ids = set(user_ids)

        # 1. Remove group_id from users who have it but are not in target_ids
        users_to_remove = await User.find({"group_ids": group_id}).to_list()
        removed_count = 0
        for u in users_to_remove:
            if str(u.id) not in target_ids:
                u.group_ids = [gid for gid in u.group_ids if gid != group_id]
                u.updated_at = datetime.now(timezone.utc)
                await u.save()
                removed_count += 1

        # 2. Add group_id to target users who don't have it
        added_count = 0
        for uid in target_ids:
            try:
                obj_id = PydanticObjectId(uid)
                u = await User.get(obj_id)
                if u and group_id not in u.group_ids:
                    u.group_ids.append(group_id)
                    u.updated_at = datetime.now(timezone.utc)
                    await u.save()
                    added_count += 1
            except Exception:
                continue

        current_count = await User.find({"group_ids": group_id}).count()
        return {
            "group_id": group_id,
            "assigned_count": current_count,
            "added": added_count,
            "removed": removed_count,
        }

    async def update(
        self,
        group_id: str,
        data: PermissionGroupUpdate,
        current_user: User,
    ) -> dict[str, Any]:
        group = await self._get_group_doc(group_id)

        update_data = data.model_dump(exclude_unset=True)

        if "name" in update_data:
            existing = await self.repo.get_by_name(update_data["name"])
            if existing and str(existing.id) != group_id:
                raise AppException(
                    message="Permission group already exists",
                    code=409,
                )

        if "permission_ids" in update_data:
            await self._validate_permissions(update_data["permission_ids"])

        for field, value in update_data.items():
            setattr(group, field, value)

        group.mark_updated(current_user.id)
        updated = await self.repo.update(group)
        user_count = await User.find({"group_ids": group_id}).count()
        return self._serialize_group(updated, user_count)

    async def delete(
        self,
        group_id: str,
    ) -> None:
        group = await self._get_group_doc(group_id)
        await self.repo.delete(group)

    async def export_csv(self) -> StreamingResponse:
        import io
        from src.common.csv_service import CSVService

        groups = await self.repo.get_all()
        all_perms = await self.permission_repo.get_all()
        perm_id_to_code = {str(p.id): p.code for p in all_perms}

        rows = []
        for g in groups:
            codes = []
            for pid in g.permission_ids:
                code = perm_id_to_code.get(str(pid))
                if code:
                    codes.append(code)
                else:
                    codes.append(str(pid))

            rows.append({
                "name": g.name or "",
                "description": g.description or "",
                "permissions": ";".join(codes),
                "is_active": "true" if g.is_active else "false",
            })

        columns = ["name", "description", "permissions", "is_active"]
        csv_bytes = CSVService.generate(rows, columns)

        return StreamingResponse(
            io.BytesIO(csv_bytes),
            media_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="permission_groups_export.csv"'
            },
        )

    async def import_csv(
        self,
        file_content: bytes,
        current_user: User,
    ) -> dict:
        from src.common.csv_service import CSVService

        try:
            columns, rows = CSVService.read(file_content)
        except Exception as e:
            raise AppException(message=f"Failed to parse CSV: {str(e)}", code=400)

        CSVService.validate_columns(columns, {"name"})

        all_perms = await self.permission_repo.get_all()
        code_to_perm = {p.code.lower(): p for p in all_perms}
        id_to_perm = {str(p.id): p for p in all_perms}

        total_rows = len(rows)
        created_count = 0
        updated_count = 0
        failed_count = 0
        created_items: list[str] = []
        updated_items: list[str] = []
        errors: list[dict] = []

        for idx, row in enumerate(rows, start=2):
            name = (row.get("name") or "").strip()
            description = (row.get("description") or "").strip() or None
            perms_str = (row.get("permissions") or "").strip()
            is_active_val = (row.get("is_active") or "true").strip().lower()
            is_active = is_active_val not in ("false", "0", "no", "inactive")

            if not name:
                failed_count += 1
                errors.append({
                    "row": idx,
                    "error": "'name' is required."
                })
                continue

            perm_codes = []
            if perms_str:
                norm = perms_str.replace(";", ",").replace("|", ",")
                perm_codes = [c.strip() for c in norm.split(",") if c.strip()]

            resolved_perm_ids = []
            missing_codes = []
            for code_or_id in perm_codes:
                if code_or_id.lower() in code_to_perm:
                    resolved_perm_ids.append(str(code_to_perm[code_or_id.lower()].id))
                elif code_or_id in id_to_perm:
                    resolved_perm_ids.append(str(id_to_perm[code_or_id].id))
                else:
                    missing_codes.append(code_or_id)

            unique_perm_ids = list(dict.fromkeys(resolved_perm_ids))

            existing = await self.repo.get_by_name(name)
            if existing:
                if description is not None:
                    existing.description = description
                existing.permission_ids = unique_perm_ids
                existing.is_active = is_active
                existing.mark_updated(current_user.id)
                await self.repo.update(existing)
                updated_count += 1
                updated_items.append(f"{name} ({len(unique_perm_ids)} permissions)")
            else:
                new_group = PermissionGroup(
                    name=name,
                    description=description,
                    permission_ids=unique_perm_ids,
                    is_active=is_active,
                    created_by=current_user.id,
                    updated_by=current_user.id,
                )
                await self.repo.create(new_group)
                created_count += 1
                created_items.append(f"{name} ({len(unique_perm_ids)} permissions)")

            if missing_codes:
                errors.append({
                    "row": idx,
                    "warning": f"Group '{name}': skipped unknown permission codes: {', '.join(missing_codes)}"
                })

        return {
            "total_rows": total_rows,
            "created_count": created_count,
            "updated_count": updated_count,
            "failed_count": failed_count,
            "created_items": created_items,
            "updated_items": updated_items,
            "errors": errors,
        }
