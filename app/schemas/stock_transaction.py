from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StockTransactionCreate(BaseModel):
    product_id: int
    warehouse_id: int
    transaction_type: str
    quantity: int
    reference_type: str | None = None
    reference_id: int | None = None


class StockTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    warehouse_id: int
    transaction_type: str
    quantity: int
    reference_type: str | None
    reference_id: int | None
    created_at: datetime
