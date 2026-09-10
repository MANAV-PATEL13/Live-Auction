from pydantic import BaseModel, EmailStr, Field


class UserCSVRow(BaseModel):
    first_name : str
    middle_name : str | None = None
    last_name : str

    roll_no : str

    email : EmailStr

    mobile : str | None = None
    image_url : str | None = None


class UserImportRowReport(BaseModel):
    row : int
    status : str
    reason : str | None = None


class UserImportSummary(BaseModel):
    total_rows : int
    created : int
    failed : int
    report : list[UserImportRowReport]


class UserBasePriceImportSummary(BaseModel):
    total_rows : int
    created : int
    failed : int
    report : list[UserImportRowReport]


class UserBasePriceCSVRow(BaseModel):
    roll_no: str
    base_price: int = Field(
        ge=0
    )