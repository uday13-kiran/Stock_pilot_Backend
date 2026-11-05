from pydantic import BaseModel, ConfigDict


class SalesReturnItemCreate(BaseModel):
    return_id: int
    product_id: int
    quantity: int
    unit_price: float
    total_price: float


class SalesReturnItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    return_id: int
    product_id: int
    quantity: int
    unit_price: float
    total_price: float
