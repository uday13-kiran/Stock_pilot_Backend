from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SaleCreate(BaseModel):
    customer_id: int
    user_id: int
    warehouse_id: int
    sale_date: datetime
    subtotal: float = 0
    discount_amount: float = 0
    tax_amount: float = 0
    total_amount: float = 0
    status: str


class SaleUpdate(BaseModel):
    status: str | None = None


class SaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    user_id: int
    warehouse_id: int
    sale_date: datetime
    subtotal: float
    discount_amount: float
    tax_amount: float
    total_amount: float
    status: str
