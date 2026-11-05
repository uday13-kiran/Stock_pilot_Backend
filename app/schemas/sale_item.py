from pydantic import BaseModel, ConfigDict


class SaleItemCreate(BaseModel):
    sale_id: int
    product_id: int
    quantity: int
    unit_price: float
    discount_amount: float = 0
    tax_amount: float = 0
    total_price: float


class SaleItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sale_id: int
    product_id: int
    quantity: int
    unit_price: float
    discount_amount: float
    tax_amount: float
    total_price: float
