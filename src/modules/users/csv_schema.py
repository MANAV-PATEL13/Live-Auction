from pydantic import BaseModel, EmailStr


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


