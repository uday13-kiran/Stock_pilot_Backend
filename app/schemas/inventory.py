
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InventoryCreate(BaseModel):
    product_id: int = Field(gt=0)
    warehouse_id: int = Field(gt=0)
    quantity: int = Field(default=0, ge=0)
    reserved_quantity: int = Field(default=0, ge=0)


class InventoryUpdate(BaseModel):
    quantity: int = Field(ge=0)


class InventoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    warehouse_id: int
    quantity: int
    reserved_quantity: int
    available_quantity: int
    updated_at: datetime | None = None