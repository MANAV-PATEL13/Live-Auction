import csv
import io
import re
from datetime import datetime, timezone
from typing import Any
from beanie import PydanticObjectId

from src.common.exceptions import ConflictException, NotFoundException
from src.modules.registration.model import Registration
from src.modules.registration.repository import RegistrationRepository
from src.modules.registration.schema import (
    RegistrationCreate,
    RegistrationUpdate,
    DuplicateMatchItem,
    UnmatchedRowItem,
)
from src.modules.users.model import User


def parse_multiselect_answers(raw_val: Any) -> list[str]:
    """Parse comma/newline separated answers into a clean list of strings while trimming whitespace."""
    if raw_val is None:
        return []
    s = str(raw_val).strip()
    if not s or s.lower() in ["none", "nan", "null", "-", ""]:
        return []

    # If already a list
    if isinstance(raw_val, list):
        return [str(x).strip() for x in raw_val if str(x).strip()]

    # First check if there are newlines
    if "\n" in s:
        items = s.split("\n")
    else:
        # Split by comma if not inside quotes
        items = [p.strip() for p in re.split(r",\s*(?=[A-Za-z0-9])", s) if p.strip()]

    # Filter out empty and clean up trailing periods if only a single punctuation
    cleaned = []
    for item in items:
        cleaned_item = item.strip()
        if cleaned_item and cleaned_item not in cleaned:
            cleaned.append(cleaned_item)
    return cleaned


class RegistrationService:

    def __init__(self, repository: RegistrationRepository):
        self.repository = repository

    async def get_by_user_id(self, user_id: PydanticObjectId) -> Registration | None:
        return await self.repository.get_by_user_id(user_id)

    async def get_by_id(self, registration_id: PydanticObjectId) -> Registration:
        registration = await self.repository.get_by_id(registration_id)
        if not registration:
            raise NotFoundException("Registration not found")
        return registration

    async def create(
        self,
        data: RegistrationCreate,
        current_user: User,
    ) -> Registration:
        existing = await self.repository.get_by_user_id(current_user.id)
        if existing:
            raise ConflictException("User has already completed registration")

        registration = Registration(
            user_id=current_user.id,
            apc_year=datetime.now(timezone.utc).year,
            games=data.games,
            experience_years=data.experience_years,
            critical_situation=data.critical_situation,
            creative_talent=data.creative_talent,
            sportsmanship=data.sportsmanship,
            preference=data.preference,
            raw_responses=data.raw_responses,
            created_by=current_user.id,
            updated_by=current_user.id,
        )

        created_registration = await self.repository.create(registration)
        current_user.is_registered = True
        await current_user.save()

        return created_registration

    async def update(
        self,
        registration_id: PydanticObjectId,
        data: RegistrationUpdate,
        current_user: User,
    ) -> Registration:
        registration = await self.repository.get_by_id(registration_id)
        if not registration:
            raise NotFoundException("Registration not found")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(registration, field, value)

        registration.mark_updated(current_user.id)
        return await self.repository.update(registration)

    async def get_all(self) -> list[Registration]:
        return await self.repository.get_all()

    async def delete(self, registration_id: PydanticObjectId) -> bool:
        registration = await self.repository.get_by_id(registration_id)
        if not registration:
            raise NotFoundException("Registration not found")

        user = await User.get(registration.user_id)
        if user:
            user.is_registered = False
            await user.save()

        await self.repository.delete(registration)
        return True

    async def delete_by_user_id(self, user_id: PydanticObjectId) -> bool:
        registration = await self.repository.get_by_user_id(user_id)
        if not registration:
            raise NotFoundException("Registration not found for this user")

        user = await User.get(user_id)
        if user:
            user.is_registered = False
            await user.save()

        await self.repository.delete(registration)
        return True

    # =========================================================================
    # IMPORT RESPONSES FROM CSV (GOOGLE FORMS / EXCEL IMPORT)
    # =========================================================================

    async def import_responses_from_csv(
        self,
        file_content: bytes,
        current_user_id: PydanticObjectId | None = None,
    ) -> dict[str, Any]:
        """
        Import registration responses from CSV.
        - Identifies user by unique email first.
        - If matching by roll_no or name, checks for duplicates and reports them.
        - Populates all 6 questions and marks user as registered.
        """
        try:
            content_str = file_content.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                content_str = file_content.decode("latin-1")
            except Exception:
                raise ValueError("CSV file encoding must be UTF-8 or Latin-1")

        reader = csv.DictReader(io.StringIO(content_str))
        if not reader.fieldnames:
            raise ValueError("CSV file is empty or has no header row")

        # Map column headers to question keys flexibly
        header_map = self._resolve_column_headers(reader.fieldnames)

        total_rows = 0
        imported_count = 0
        updated_count = 0
        duplicates: list[dict[str, Any]] = []
        unmatched: list[dict[str, Any]] = []
        errors: list[str] = []

        all_users = await User.find().to_list()
        # Build lookup maps
        email_map: dict[str, User] = {}
        roll_map: dict[str, list[User]] = {}
        name_map: dict[str, list[User]] = {}

        for u in all_users:
            if u.email:
                email_map[u.email.strip().lower()] = u
            if u.roll_no:
                r_key = u.roll_no.strip().lower()
                roll_map.setdefault(r_key, []).append(u)
            if u.name:
                n_key = u.name.strip().lower()
                name_map.setdefault(n_key, []).append(u)
            # Also combine first + last
            full_n = f"{u.first_name or ''} {u.last_name or ''}".strip().lower()
            if full_n and full_n not in name_map:
                name_map.setdefault(full_n, []).append(u)

        row_idx = 1
        for row in reader:
            row_idx += 1
            # Skip empty rows
            if not any(str(v or "").strip() for v in row.values()):
                continue

            total_rows += 1

            raw_email = row.get(header_map.get("email", "")) or ""
            raw_roll = row.get(header_map.get("roll_no", "")) or ""
            raw_name = row.get(header_map.get("name", "")) or ""

            email_clean = str(raw_email).strip().lower() if raw_email else ""
            roll_clean = str(raw_roll).strip().lower() if raw_roll else ""
            name_clean = str(raw_name).strip().lower() if raw_name else ""

            matched_user: User | None = None
            is_duplicate = False

            # 1. Match by Email (Primary & Unique)
            if email_clean and email_clean in email_map:
                matched_user = email_map[email_clean]

            # 2. Match by Roll No (Check for duplicates)
            elif roll_clean and roll_clean in roll_map:
                candidates = roll_map[roll_clean]
                if len(candidates) > 1:
                    is_duplicate = True
                    duplicates.append({
                        "row_number": row_idx,
                        "match_type": "roll_no",
                        "search_value": str(raw_roll).strip(),
                        "matched_users": [
                            {"id": str(u.id), "name": u.name, "email": u.email, "roll_no": u.roll_no}
                            for u in candidates
                        ],
                        "message": f"Multiple ({len(candidates)}) users have roll number '{raw_roll}'. Use email to match.",
                    })
                else:
                    matched_user = candidates[0]

            # 3. Match by Name (Check for duplicates)
            elif name_clean and name_clean in name_map:
                candidates = name_map[name_clean]
                if len(candidates) > 1:
                    is_duplicate = True
                    duplicates.append({
                        "row_number": row_idx,
                        "match_type": "name",
                        "search_value": str(raw_name).strip(),
                        "matched_users": [
                            {"id": str(u.id), "name": u.name, "email": u.email, "roll_no": u.roll_no}
                            for u in candidates
                        ],
                        "message": f"Multiple ({len(candidates)}) users named '{raw_name}'. Use email or unique roll number to match.",
                    })
                else:
                    matched_user = candidates[0]

            # If duplicate conflict, skip assigning to wrong user
            if is_duplicate:
                continue

            # If no user matched
            if not matched_user:
                unmatched.append({
                    "row_number": row_idx,
                    "roll_no": str(raw_roll).strip() if raw_roll else None,
                    "name": str(raw_name).strip() if raw_name else None,
                    "email": str(raw_email).strip() if raw_email else None,
                    "reason": "User not found in system by email, roll number, or name.",
                })
                continue

            # Extract Question Answers
            games_val = row.get(header_map.get("games", "")) or ""
            exp_val = row.get(header_map.get("experience_years", "")) or ""
            crit_val = row.get(header_map.get("critical_situation", "")) or ""
            creat_val = row.get(header_map.get("creative_talent", "")) or ""
            sport_val = row.get(header_map.get("sportsmanship", "")) or ""
            pref_val = row.get(header_map.get("preference", "")) or ""

            games = parse_multiselect_answers(games_val)
            experience_years = str(exp_val).strip() if exp_val else None
            critical_situation = parse_multiselect_answers(crit_val)
            creative_talent = parse_multiselect_answers(creat_val)
            sportsmanship = parse_multiselect_answers(sport_val)
            preference = parse_multiselect_answers(pref_val)

            # Check existing registration for this user
            reg = await self.repository.get_by_user_id(matched_user.id)
            if reg:
                reg.games = games
                reg.experience_years = experience_years
                reg.critical_situation = critical_situation
                reg.creative_talent = creative_talent
                reg.sportsmanship = sportsmanship
                reg.preference = preference
                reg.raw_responses = {k: str(v) for k, v in row.items() if v}
                if current_user_id:
                    reg.mark_updated(current_user_id)
                await self.repository.update(reg)
                updated_count += 1
            else:
                reg = Registration(
                    user_id=matched_user.id,
                    apc_year=datetime.now(timezone.utc).year,
                    games=games,
                    experience_years=experience_years,
                    critical_situation=critical_situation,
                    creative_talent=creative_talent,
                    sportsmanship=sportsmanship,
                    preference=preference,
                    raw_responses={k: str(v) for k, v in row.items() if v},
                    created_by=current_user_id,
                    updated_by=current_user_id,
                )
                await self.repository.create(reg)
                imported_count += 1

            # Mark user as registered
            if not matched_user.is_registered:
                matched_user.is_registered = True
                await matched_user.save()

        return {
            "total_rows": total_rows,
            "imported_count": imported_count,
            "updated_count": updated_count,
            "duplicates": duplicates,
            "unmatched": unmatched,
            "errors": errors,
        }

    @staticmethod
    def _resolve_column_headers(columns: list[str]) -> dict[str, str]:
        """Map CSV column headers to known keys flexibly."""
        mapping: dict[str, str] = {}
        for col in columns:
            c_clean = col.strip().lower().replace("_", " ").replace("-", " ")

            # 1. Email
            if "email" in c_clean and "email" not in mapping:
                mapping["email"] = col

            # 2. Roll No
            elif any(k in c_clean for k in ["roll no", "rollno", "roll number", "roll_no", "roll"]) and "roll_no" not in mapping:
                mapping["roll_no"] = col

            # 3. Name
            elif any(k in c_clean for k in ["full name", "student name", "participant name", "player name", "name"]) and "name" not in mapping:
                if "games" not in c_clean and "task" not in c_clean:
                    mapping["name"] = col

            # 4. Games enthusiasm ("Which games do you play with enthusiasm?")
            elif any(k in c_clean for k in ["enthusiasm", "which games", "games you play", "games", "sports"]) and "games" not in mapping:
                mapping["games"] = col

            # 5. Experience ("How many years of experience do you have in the Bhaktiparv?")
            elif any(k in c_clean for k in ["experience", "years of experience", "bhaktiparv", "experience in"]) and "experience_years" not in mapping:
                mapping["experience_years"] = col

            # 6. Critical situation ("How do you respond in critical situation?")
            elif any(k in c_clean for k in ["critical situation", "critical", "respond in critical"]) and "critical_situation" not in mapping:
                mapping["critical_situation"] = col

            # 7. Creative Task & Talent ("Creative Task & Talent")
            elif any(k in c_clean for k in ["creative", "talent", "creative task"]) and "creative_talent" not in mapping:
                mapping["creative_talent"] = col

            # 8. Sportsmanship ("Sportsmanship")
            elif any(k in c_clean for k in ["sportsmanship", "sportsman spirit", "sportsman"]) and "sportsmanship" not in mapping:
                mapping["sportsmanship"] = col

            # 9. Preference ("What do you prefer?")
            elif any(k in c_clean for k in ["prefer", "preference", "what do you prefer", "teamwork"]) and "preference" not in mapping:
                mapping["preference"] = col

        return mapping

    @staticmethod
    def format_registration(reg: Registration | None) -> dict[str, Any] | None:
        if reg is None:
            return None
        return {
            "id": str(reg.id),
            "user_id": str(reg.user_id),
            "apc_year": getattr(reg, "apc_year", None) or (reg.created_at.year if getattr(reg, "created_at", None) else datetime.now(timezone.utc).year),
            "games": reg.games or [],
            "experience_years": reg.experience_years,
            "critical_situation": reg.critical_situation or [],
            "creative_talent": reg.creative_talent or [],
            "sportsmanship": reg.sportsmanship or [],
            "preference": reg.preference or [],
            "raw_responses": getattr(reg, "raw_responses", {}) or {},
            "sports": reg.sports_map,
            "created_by": str(reg.created_by) if reg.created_by else None,
            "updated_by": str(reg.updated_by) if reg.updated_by else None,
            "created_at": reg.created_at.isoformat() if getattr(reg, "created_at", None) else None,
            "updated_at": reg.updated_at.isoformat() if getattr(reg, "updated_at", None) else None,
        }