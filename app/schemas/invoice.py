from datetime import datetime

from pydantic import BaseModel, ConfigDict


class InvoiceCreate(BaseModel):
    sale_id: int
    invoice_date: datetime
    subtotal: float
    tax_amount: float
    total_amount: float
    status: str


class InvoiceUpdate(BaseModel):
    status: str | None = None


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sale_id: int
    invoice_date: datetime
    subtotal: float
    tax_amount: float
    total_amount: float
    status: str
