from pydantic import BaseModel, ConfigDict


class StockTransferItemCreate(BaseModel):
    transfer_id: int
    product_id: int
    requested_quantity: int
    dispatched_quantity: int = 0
    received_quantity: int = 0


class StockTransferItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transfer_id: int
    product_id: int
    requested_quantity: int
    dispatched_quantity: int
    received_quantity: int
