from pydantic import BaseModel, ConfigDict


class InvoiceItemCreate(BaseModel):
    invoice_id: int
    product_id: int
    quantity: int
    unit_price: float
    total_price: float


class InvoiceItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    product_id: int
    quantity: int
    unit_price: float
    total_price: float
