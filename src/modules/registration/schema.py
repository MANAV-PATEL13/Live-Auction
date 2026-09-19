from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class RegistrationCreate(BaseModel):
    games: list[str] = Field(default_factory=list)
    experience_years: str | None = None
    critical_situation: list[str] = Field(default_factory=list)
    creative_talent: list[str] = Field(default_factory=list)
    sportsmanship: list[str] = Field(default_factory=list)
    preference: list[str] = Field(default_factory=list)
    raw_responses: dict[str, Any] = Field(default_factory=dict)


class RegistrationUpdate(BaseModel):
    games: list[str] | None = None
    experience_years: str | None = None
    critical_situation: list[str] | None = None
    creative_talent: list[str] | None = None
    sportsmanship: list[str] | None = None
    preference: list[str] | None = None
    raw_responses: dict[str, Any] | None = None


class RegistrationResponse(BaseModel):
    id: str
    user_id: str
    apc_year: int
    games: list[str]
    experience_years: str | None = None
    critical_situation: list[str]
    creative_talent: list[str]
    sportsmanship: list[str]
    preference: list[str]
    raw_responses: dict[str, Any] = Field(default_factory=dict)
    sports: dict[str, str] = Field(default_factory=dict)
    created_by: str | None = None
    updated_by: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class DuplicateMatchItem(BaseModel):
    row_number: int
    match_type: str  # "roll_no" or "name"
    search_value: str
    matched_users: list[dict[str, Any]]
    message: str


class UnmatchedRowItem(BaseModel):
    row_number: int
    roll_no: str | None = None
    name: str | None = None
    email: str | None = None
    reason: str


class RegistrationCSVImportResponse(BaseModel):
    total_rows: int
    imported_count: int
    updated_count: int
    duplicates: list[DuplicateMatchItem] = Field(default_factory=list)
    unmatched: list[UnmatchedRowItem] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)