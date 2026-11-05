from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GoodsReceiptCreate(BaseModel):
    purchase_order_id: int
    warehouse_id: int
    received_date: datetime
    status: str
    notes: str | None = None


class GoodsReceiptUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None


class GoodsReceiptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    purchase_order_id: int
    warehouse_id: int
    received_date: datetime
    status: str
    notes: str | None
