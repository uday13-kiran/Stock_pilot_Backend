from pydantic import BaseModel, ConfigDict


class WarehouseUserCreate(BaseModel):
    user_id: int
    warehouse_id: int
    role: str | None = None


class WarehouseUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    warehouse_id: int
    role: str | None
