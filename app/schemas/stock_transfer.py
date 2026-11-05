from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StockTransferCreate(BaseModel):
    from_warehouse_id: int
    to_warehouse_id: int
    transfer_date: datetime
    status: str = "REQUESTED"
    notes: str | None = None


class StockTransferUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None


class StockTransferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_warehouse_id: int
    to_warehouse_id: int
    transfer_date: datetime
    status: str
    notes: str | None
