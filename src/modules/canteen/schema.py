from pydantic import BaseModel, Field

class MenuItemCreate(BaseModel):

    name : str = Field(min_length=2)
    description : str | None = None
    price : float = Field(gt=0)
    image_url : str
    is_show : bool = True


class MenuItemUpdate(BaseModel):

    name : str | None = Field( default=None, min_length=2)
    price : float | None = Field( default=None, gt=0)
    image_url : str | None = None
    description : str | None = None
    is_show : bool | None = None


class MenuItemResponse(BaseModel):
    id: str

    name: str
    description: str | None
    category: str
    price: float
    image_url: str | None
    is_available: bool

    created_by: str
    updated_by: str
    created_at: str
    updated_at: str