from pydantic import BaseModel, ConfigDict


class WarehouseCreate(BaseModel):
    name: str
    location: str
    address: str | None = None
    is_active: bool = True


class WarehouseUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    address: str | None = None
    is_active: bool | None = None


class WarehouseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location: str
    address: str | None
    is_active: bool
