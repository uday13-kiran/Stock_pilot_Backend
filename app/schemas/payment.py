from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PaymentCreate(BaseModel):
    invoice_id: int
    amount: float
    payment_method: str
    payment_date: datetime
    status: str = "PENDING"


class PaymentUpdate(BaseModel):
    status: str | None = None


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    amount: float
    payment_method: str
    payment_date: datetime
    status: str
