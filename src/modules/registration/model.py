from datetime import datetime, timezone
from typing import Any

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, IndexModel

from src.common.audit import AuditMixin


class Registration(Document, AuditMixin):

    user_id: PydanticObjectId
    apc_year: int = Field(default_factory=lambda: datetime.now(timezone.utc).year)

    # 1. Which games do you play with enthusiasm? (Single or Multi-select)
    games: list[str] = Field(default_factory=list)

    # 2. How many years of experience do you have in the Bhaktiparv?
    experience_years: str | None = None

    # 3. How do you respond in critical situation? (Single or Multi-select)
    critical_situation: list[str] = Field(default_factory=list)

    # 4. Creative Task & Talent (Single or Multi-select)
    creative_talent: list[str] = Field(default_factory=list)

    # 5. Sportsmanship (Single or Multi-select)
    sportsmanship: list[str] = Field(default_factory=list)

    # 6. What do you prefer? (Single or Multi-select, e.g., Working Individually, Teamwork)
    preference: list[str] = Field(default_factory=list)

    # Full raw responses from imported questionnaire CSV
    raw_responses: dict[str, Any] = Field(default_factory=dict)

    @property
    def sports_map(self) -> dict[str, str]:
        """Convert enthusiasm games list into a sports map for auction & leaderboard displays"""
        if not self.games:
            return {}
        result = {}
        for g in self.games:
            clean_k = g.strip().lower().replace(" ", "_").replace("-", "_")
            if clean_k:
                result[clean_k] = "EXPERT"
        return result

    class Settings:
        name = "registrations"

        indexes = [
            IndexModel(
                [("user_id", ASCENDING)],
                unique=True,
                name="uq_registration_user",
            ),
        ]