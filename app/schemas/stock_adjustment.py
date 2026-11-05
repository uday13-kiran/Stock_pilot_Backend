from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StockAdjustmentCreate(BaseModel):
    product_id: int
    warehouse_id: int
    user_id: int
    quantity: int
    reason: str
    approved: bool = False


class StockAdjustmentUpdate(BaseModel):
    approved: bool | None = None
    reason: str | None = None


class StockAdjustmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    warehouse_id: int
    user_id: int
    quantity: int
    reason: str
    approved: bool
    created_at: datetime
